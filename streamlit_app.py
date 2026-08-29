from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="Balotario de Aviación",
    page_icon="✈️",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "preguntas.csv"
EXPECTED_EXAM_SIZE = 100

# ----------------------------
# SUPABASE / IDENTIDAD
# ----------------------------
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )

def learner_id(alias: str, pin: str) -> str:
    pepper = st.secrets["PROFILE_PEPPER"]
    raw = f"{alias.strip().lower()}::{pin}::{pepper}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def login_screen():
    st.title("✈️ Balotario de Aviación")
    st.caption("Tu progreso se guarda online para que puedas continuar desde cualquier dispositivo.")
    with st.form("login"):
        alias = st.text_input("Nombre o alias", placeholder="Ej.: Luana")
        pin = st.text_input("PIN personal", type="password", max_chars=20)
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        if not alias.strip() or len(pin) < 4:
            st.error("Ingresa un alias y un PIN de al menos 4 caracteres.")
            return
        st.session_state.learner_id = learner_id(alias, pin)
        st.session_state.alias = alias.strip()
        st.rerun()

if "learner_id" not in st.session_state:
    login_screen()
    st.stop()

sb = get_supabase()
LEARNER_ID = st.session_state.learner_id

# ----------------------------
# PREGUNTAS
# ----------------------------
@st.cache_data
def load_questions():
    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    bool_map = {"True": True, "False": False, "true": True, "false": False, "1": True, "0": False}
    if "requiere_figura" in df.columns:
        df["requiere_figura"] = df["requiere_figura"].map(bool_map).fillna(False)
    else:
        df["requiere_figura"] = False
    records = df.to_dict("records")
    # Elimina duplicados por ID sin alterar el banco original.
    by_id = {}
    for q in records:
        by_id[q["id"]] = q
    return list(by_id.values())

questions = load_questions()
by_id = {q["id"]: q for q in questions}
themes = sorted({q["tema"] for q in questions})

# ----------------------------
# PROGRESO EN SUPABASE
# ----------------------------
def get_progress_map() -> dict[str, dict]:
    response = (
        sb.table("aviation_progress")
        .select("*")
        .eq("learner_id", LEARNER_ID)
        .execute()
    )
    return {row["question_id"]: row for row in (response.data or [])}

def progress_for(qid: str, progress: dict[str, dict]) -> dict:
    return progress.get(
        qid,
        {
            "learner_id": LEARNER_ID,
            "question_id": qid,
            "seen": 0,
            "correct": 0,
            "wrong": 0,
            "starred": False,
            "last_answer": None,
            "last_seen": None,
        },
    )

def record_answer(question_id: str, selected: str, correct_answer: str) -> None:
    p = progress_for(question_id, get_progress_map())
    is_correct = selected == correct_answer
    payload = {
        "learner_id": LEARNER_ID,
        "question_id": question_id,
        "seen": int(p["seen"]) + 1,
        "correct": int(p["correct"]) + int(is_correct),
        "wrong": int(p["wrong"]) + int(not is_correct),
        "starred": bool(p["starred"]),
        "last_answer": selected,
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }
    (
        sb.table("aviation_progress")
        .upsert(payload, on_conflict="learner_id,question_id")
        .execute()
    )

def set_star(question_id: str, starred: bool) -> None:
    p = progress_for(question_id, get_progress_map())
    payload = {
        "learner_id": LEARNER_ID,
        "question_id": question_id,
        "seen": int(p["seen"]),
        "correct": int(p["correct"]),
        "wrong": int(p["wrong"]),
        "starred": bool(starred),
        "last_answer": p.get("last_answer"),
        "last_seen": p.get("last_seen"),
    }
    (
        sb.table("aviation_progress")
        .upsert(payload, on_conflict="learner_id,question_id")
        .execute()
    )

def reset_progress() -> None:
    (
        sb.table("aviation_progress")
        .delete()
        .eq("learner_id", LEARNER_ID)
        .execute()
    )

# ----------------------------
# HELPERS
# ----------------------------
def eligible_questions(questions, selected_themes, mode, progress):
    pool = [q for q in questions if q["tema"] in selected_themes]
    if mode == "Todas":
        return pool
    if mode == "No vistas":
        return [q for q in pool if int(progress_for(q["id"], progress)["seen"]) == 0]
    if mode == "Errores":
        return [q for q in pool if int(progress_for(q["id"], progress)["wrong"]) > 0]
    if mode == "Marcadas":
        return [q for q in pool if bool(progress_for(q["id"], progress)["starred"])]
    return pool

def choose_new_question(pool, current_id=None):
    if not pool:
        return None
    candidates = [q for q in pool if q["id"] != current_id]
    return random.choice(candidates or pool)

def show_question(q, key_prefix, disabled=False):
    st.subheader(f"Pregunta {q['numero']}")
    st.caption(f"Tema: {q['tema']}")
    if q.get("requiere_figura", False):
        st.warning(
            "Esta pregunta hace referencia a una figura, gráfico o carta. "
            "Consulta el material gráfico original si lo necesitas."
        )
    st.markdown(f"### {q['pregunta']}")
    option_labels = {
        "A": f"A) {q['A']}",
        "B": f"B) {q['B']}",
        "C": f"C) {q['C']}",
    }
    selected_label = st.radio(
        "Selecciona una respuesta:",
        options=list(option_labels.values()),
        index=None,
        key=f"{key_prefix}_{q['id']}",
        disabled=disabled,
    )
    return None if selected_label is None else selected_label[0]

# ----------------------------
# CABECERA / SIDEBAR
# ----------------------------
st.title("✈️ Balotario de Aviación")
st.caption("Estudio, repaso de errores y simulacros de 100 preguntas")

with st.sidebar:
    st.write(f"👤 **{st.session_state.alias}**")
    if st.button("Cerrar sesión"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.header("Configuración")
    section = st.radio("Modo", ["Estudio", "Simulacro 100", "Estadísticas"])
    selected_themes = st.multiselect("Temas", themes, default=themes)
    st.divider()
    st.write(f"Preguntas del banco: **{len(questions)}**")

    with st.expander("Reiniciar todo el progreso"):
        confirm_reset = st.checkbox("Sí, quiero borrar mi progreso")
        if st.button("Borrar progreso", disabled=not confirm_reset):
            reset_progress()
            keep = {"learner_id", "alias"}
            for key in list(st.session_state.keys()):
                if key not in keep:
                    del st.session_state[key]
            st.rerun()

progress = get_progress_map()

seen_unique = sum(1 for q in questions if int(progress_for(q["id"], progress)["seen"]) > 0)
total_correct = sum(int(progress_for(q["id"], progress)["correct"]) for q in questions)
total_wrong = sum(int(progress_for(q["id"], progress)["wrong"]) for q in questions)
total_attempts = total_correct + total_wrong
accuracy = (100 * total_correct / total_attempts) if total_attempts else 0.0
starred_count = sum(int(bool(progress_for(q["id"], progress)["starred"])) for q in questions)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Vistas", f"{seen_unique}/{len(questions)}")
m2.metric("Precisión", f"{accuracy:.1f}%")
m3.metric("Errores", total_wrong)
m4.metric("Marcadas", starred_count)
st.divider()

# ----------------------------
# ESTUDIO
# ----------------------------
if section == "Estudio":
    study_mode = st.selectbox(
        "Qué quieres practicar",
        ["Todas", "No vistas", "Errores", "Marcadas"],
    )
    progress = get_progress_map()
    pool = eligible_questions(questions, selected_themes, study_mode, progress)
    st.caption(f"Preguntas disponibles con este filtro: {len(pool)}")

    if not selected_themes:
        st.info("Selecciona al menos un tema.")
        st.stop()

    signature_key = f"{study_mode}|{'|'.join(selected_themes)}"
    if st.session_state.get("study_signature") != signature_key:
        st.session_state.study_signature = signature_key
        st.session_state.study_qid = None
        st.session_state.study_answered = False
        st.session_state.study_selected = None

    current_id = st.session_state.get("study_qid")
    if st.session_state.get("study_answered", False) and current_id:
        current = next(
            (q for q in questions if q["id"] == current_id and q["tema"] in selected_themes),
            None,
        )
    else:
        current = next((q for q in pool if q["id"] == current_id), None)

    if current is None:
        if not pool:
            st.success("No hay preguntas en este filtro.")
            st.stop()
        current = choose_new_question(pool)
        st.session_state.study_qid = current["id"]
        st.session_state.study_answered = False
        st.session_state.study_selected = None

    p = progress_for(current["id"], progress)
    star_now = st.checkbox(
        "⭐ Marcar para repasar",
        value=bool(p["starred"]),
        key=f"star_{current['id']}",
    )
    if star_now != bool(p["starred"]):
        set_star(current["id"], star_now)
        progress = get_progress_map()

    selected = show_question(
        current,
        key_prefix="study_choice",
        disabled=st.session_state.get("study_answered", False),
    )

    if not st.session_state.get("study_answered", False):
        if st.button("Responder", type="primary", disabled=selected is None):
            record_answer(current["id"], selected, current["respuesta"])
            st.session_state.study_answered = True
            st.session_state.study_selected = selected
            st.rerun()
    else:
        selected_saved = st.session_state.get("study_selected")
        if selected_saved == current["respuesta"]:
            st.success(f"Correcto. La respuesta es {current['respuesta']}.")
        else:
            st.error(
                f"Tu respuesta fue {selected_saved}. La correcta es "
                f"{current['respuesta']}: {current[current['respuesta']]}"
            )

        if st.button("Siguiente pregunta", type="primary"):
            progress = get_progress_map()
            refreshed_pool = eligible_questions(
                questions, selected_themes, study_mode, progress
            )
            nxt = choose_new_question(refreshed_pool, current_id=current["id"])
            st.session_state.study_qid = nxt["id"] if nxt else None
            st.session_state.study_answered = False
            st.session_state.study_selected = None
            st.rerun()

# ----------------------------
# SIMULACRO
# ----------------------------
elif section == "Simulacro 100":
    exam_pool = [q for q in questions if q["tema"] in selected_themes]

    if len(exam_pool) < EXPECTED_EXAM_SIZE:
        st.warning(
            f"Con los temas seleccionados solo hay {len(exam_pool)} preguntas. "
            f"Necesitas {EXPECTED_EXAM_SIZE}."
        )
        st.stop()

    if "sim_ids" not in st.session_state:
        st.session_state.sim_ids = []
        st.session_state.sim_index = 0
        st.session_state.sim_answers = {}
        st.session_state.sim_finished = False
        st.session_state.sim_saved = False

    if not st.session_state.sim_ids:
        st.info(
            "Selecciona 100 preguntas únicas al azar. "
            "Las respuestas correctas se muestran solo al terminar."
        )
        if st.button("Iniciar simulacro de 100 preguntas", type="primary"):
            st.session_state.sim_ids = [
                q["id"] for q in random.sample(exam_pool, EXPECTED_EXAM_SIZE)
            ]
            st.session_state.sim_index = 0
            st.session_state.sim_answers = {}
            st.session_state.sim_finished = False
            st.session_state.sim_saved = False
            st.rerun()
        st.stop()

    sim_questions = [by_id[qid] for qid in st.session_state.sim_ids if qid in by_id]

    if not st.session_state.sim_finished:
        idx = st.session_state.sim_index
        current = sim_questions[idx]
        st.progress((idx + 1) / EXPECTED_EXAM_SIZE)
        st.write(f"**Pregunta {idx + 1} de {EXPECTED_EXAM_SIZE}**")

        selected = show_question(current, key_prefix=f"sim_{idx}")
        is_last = idx == EXPECTED_EXAM_SIZE - 1
        button_text = "Finalizar simulacro" if is_last else "Guardar y siguiente"

        if st.button(button_text, type="primary", disabled=selected is None):
            st.session_state.sim_answers[current["id"]] = selected
            if is_last:
                st.session_state.sim_finished = True
            else:
                st.session_state.sim_index += 1
            st.rerun()
    else:
        answers = st.session_state.sim_answers
        correct_count = sum(
            1 for q in sim_questions if answers.get(q["id"]) == q["respuesta"]
        )
        score_pct = 100 * correct_count / EXPECTED_EXAM_SIZE
        st.success(f"Resultado: {correct_count}/{EXPECTED_EXAM_SIZE} ({score_pct:.1f}%)")

        if not st.session_state.sim_saved:
            for q in sim_questions:
                selected = answers.get(q["id"])
                if selected:
                    record_answer(q["id"], selected, q["respuesta"])
            st.session_state.sim_saved = True

        wrong_rows = []
        for q in sim_questions:
            selected = answers.get(q["id"])
            if selected != q["respuesta"]:
                wrong_rows.append(
                    {
                        "Nº": q["numero"],
                        "Tema": q["tema"],
                        "Tu respuesta": selected,
                        "Correcta": q["respuesta"],
                        "Pregunta": q["pregunta"],
                    }
                )
        if wrong_rows:
            st.subheader("Preguntas falladas")
            st.dataframe(pd.DataFrame(wrong_rows), use_container_width=True, hide_index=True)
        else:
            st.balloons()
            st.write("¡100/100!")

        if st.button("Nuevo simulacro"):
            for key in [
                "sim_ids", "sim_index", "sim_answers",
                "sim_finished", "sim_saved"
            ]:
                st.session_state.pop(key, None)
            st.rerun()

# ----------------------------
# ESTADÍSTICAS
# ----------------------------
else:
    progress = get_progress_map()
    rows = []
    for theme in themes:
        qs = [q for q in questions if q["tema"] == theme]
        viewed = sum(int(progress_for(q["id"], progress)["seen"]) > 0 for q in qs)
        corr = sum(int(progress_for(q["id"], progress)["correct"]) for q in qs)
        wrong = sum(int(progress_for(q["id"], progress)["wrong"]) for q in qs)
        attempts = corr + wrong
        rows.append(
            {
                "Tema": theme,
                "Preguntas": len(qs),
                "Vistas": viewed,
                "% cubierto": round(100 * viewed / len(qs), 1) if qs else 0,
                "Aciertos": corr,
                "Errores": wrong,
                "% precisión": round(100 * corr / attempts, 1) if attempts else 0,
            }
        )

    st.subheader("Rendimiento por tema")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    weak = []
    for q in questions:
        p = progress_for(q["id"], progress)
        if int(p["seen"]) > 0:
            weak.append(
                {
                    "Nº": q["numero"],
                    "Tema": q["tema"],
                    "Vistas": p["seen"],
                    "Aciertos": p["correct"],
                    "Errores": p["wrong"],
                    "Marcada": "Sí" if p["starred"] else "No",
                    "Pregunta": q["pregunta"],
                }
            )

    if weak:
        weak_df = pd.DataFrame(weak).sort_values(
            by=["Errores", "Vistas"], ascending=[False, False]
        )
        st.subheader("Preguntas con más errores")
        st.dataframe(weak_df.head(50), use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay respuestas registradas.")
