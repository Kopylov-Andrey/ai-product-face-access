"""Локальный веб-MVP панели контроля доступа."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from app.demo import DemoResult, run_demo
from app.turnstile import TurnstileSimulator

SCENARIOS = {
    "Обычный проход": "happy",
    "Неоднозначное совпадение": "risky",
    "Подозрение на spoofing": "spoof",
    "Устаревшая политика доступа": "offline",
    "Отозванный доступ": "revoked",
    "Низкое качество кадра": "low_quality",
}

SCENARIO_CHECKS = {
    "happy": (
        ("Качество кадра", "Пройдено", "ok"),
        ("Проверка живости", "Пройдена", "ok"),
        ("Совпадение лица", "Уверенное", "ok"),
        ("Право доступа", "Активно", "ok"),
    ),
    "risky": (
        ("Качество кадра", "Пройдено", "ok"),
        ("Проверка живости", "Пройдена", "ok"),
        ("Совпадение лица", "Неоднозначное", "warn"),
        ("Право доступа", "Активно", "ok"),
    ),
    "spoof": (
        ("Качество кадра", "Пройдено", "ok"),
        ("Проверка живости", "Риск spoofing", "bad"),
        ("Совпадение лица", "Не используется", "muted"),
        ("Право доступа", "Не проверяется", "muted"),
    ),
    "offline": (
        ("Качество кадра", "Пройдено", "ok"),
        ("Проверка живости", "Пройдена", "ok"),
        ("Совпадение лица", "Уверенное", "ok"),
        ("Политика доступа", "Устарела", "warn"),
    ),
    "revoked": (
        ("Качество кадра", "Пройдено", "ok"),
        ("Проверка живости", "Пройдена", "ok"),
        ("Совпадение лица", "Уверенное", "ok"),
        ("Право доступа", "Отозвано", "bad"),
    ),
    "low_quality": (
        ("Качество кадра", "Нужен повтор", "warn"),
        ("Проверка живости", "Не запускалась", "muted"),
        ("Совпадение лица", "Не запускалось", "muted"),
        ("Право доступа", "Не проверялось", "muted"),
    ),
}

DECISION_LABELS = {
    "allow": ("Доступ разрешён", "ok"),
    "deny": ("Доступ отклонён", "bad"),
    "manual_review": ("Требуется проверка", "warn"),
}

ACTION_LABELS = {
    "open_turnstile": "Открыть турникет",
    "guard_review": "Передать событие сотруднику охраны",
    "security_review": "Передать событие службе безопасности",
    "safe_fallback_or_guard_review": "Использовать резервный сценарий",
    "access_denied": "Оставить доступ закрытым",
    "retry_or_card_fallback": "Повторить кадр или использовать карту",
    "card_fallback_or_guard_review": "Использовать карту или ручную проверку",
}

CSS = """
<style>
:root {
  --bg: #f4f6f8;
  --card: #ffffff;
  --text: #111827;
  --muted: #6b7280;
  --line: #e5e7eb;
  --nav: #0f172a;
  --blue: #2563eb;
  --green: #0f9f6e;
  --amber: #d97706;
  --red: #dc2626;
}
header[data-testid="stHeader"] {visibility: hidden; height: 0;}
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
.stApp {background: var(--bg); color: var(--text);}
.block-container {max-width: 1380px; padding-top: 2rem; padding-bottom: 3rem;}
[data-testid="stSidebar"] {background: var(--nav);}
[data-testid="stSidebar"] * {color: #e5e7eb;}
[data-testid="stSidebar"] label {font-weight: 600;}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #172033;
  border-color: #334155;
}
[data-testid="stSidebar"] .stButton > button {
  border: 0;
  border-radius: 10px;
  min-height: 44px;
  font-weight: 700;
}
.product-brand {font-size: 24px; font-weight: 800; color: #ffffff;}
.product-subtitle {font-size: 13px; color: #94a3b8; margin-top: 2px;}
.sidebar-status {
  display: flex;
  gap: 8px;
  align-items: center;
  margin: 22px 0 4px;
  font-size: 13px;
  color: #cbd5e1;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, .13);
}
.page-title {font-size: 30px; line-height: 1.2; font-weight: 800; margin: 0;}
.page-subtitle {color: var(--muted); margin-top: 6px; font-size: 14px;}
.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}
.stat-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px;
  min-height: 90px;
}
.stat-label {font-size: 12px; color: var(--muted); text-transform: uppercase;}
.stat-value {font-size: 21px; font-weight: 750; margin-top: 8px; color: var(--text);}
.section-title {font-size: 17px; font-weight: 750; margin-bottom: 14px;}
.person-card {display: flex; align-items: center; gap: 14px;}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: #e8eefc;
  color: #1d4ed8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
}
.person-name {font-size: 18px; font-weight: 750;}
.person-meta {font-size: 13px; color: var(--muted); margin-top: 3px;}
.result-box {
  border-radius: 14px;
  padding: 18px;
  margin-top: 18px;
  border: 1px solid;
}
.result-ok {background: #ecfdf5; border-color: #a7f3d0;}
.result-warn {background: #fffbeb; border-color: #fde68a;}
.result-bad {background: #fef2f2; border-color: #fecaca;}
.result-kicker {font-size: 12px; color: var(--muted); text-transform: uppercase;}
.result-title {font-size: 25px; font-weight: 800; margin-top: 5px;}
.result-detail {font-size: 14px; color: #374151; margin-top: 7px;}
.check-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 11px 0;
  border-bottom: 1px solid #eef1f4;
}
.check-row:last-child {border-bottom: 0;}
.check-name {font-size: 14px; color: #374151;}
.pill {
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
}
.pill-ok {background: #dcfce7; color: #166534;}
.pill-warn {background: #fef3c7; color: #92400e;}
.pill-bad {background: #fee2e2; color: #991b1b;}
.pill-muted {background: #f3f4f6; color: #6b7280;}
.turnstile {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: .01em;
  margin-top: 4px;
}
.gate-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 16px 18px 14px;
  min-height: 126px;
}
.gate-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}
.gate-state {font-size: 18px; font-weight: 800; color: var(--text);}
.gate-hint {font-size: 12px; color: var(--muted); margin-top: 2px;}
.gate-badge {
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .04em;
}
.gate-badge-open {background: #dcfce7; color: #166534;}
.gate-badge-closed {background: #fee2e2; color: #991b1b;}
.gate-scene {
  position: relative;
  height: 64px;
  margin-top: 12px;
  overflow: hidden;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
}
.gate-lane {
  position: absolute;
  left: 8%;
  right: 8%;
  bottom: 10px;
  height: 2px;
  background: #cbd5e1;
}
.gate-post {
  position: absolute;
  bottom: 11px;
  width: 18px;
  height: 42px;
  border-radius: 5px 5px 3px 3px;
  background: linear-gradient(180deg, #64748b, #334155);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.22);
}
.gate-post-left {left: 22%;}
.gate-post-right {right: 22%;}
.gate-light {
  position: absolute;
  width: 7px;
  height: 7px;
  top: 7px;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 50%;
}
.gate-open .gate-light {
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34,197,94,.16);
}
.gate-closed .gate-light {
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239,68,68,.14);
}
.gate-arm {
  position: absolute;
  left: calc(22% + 16px);
  top: 31px;
  width: 34%;
  height: 7px;
  border-radius: 999px;
  transform-origin: left center;
  background: repeating-linear-gradient(
    90deg,
    #e5e7eb 0 16px,
    #ef4444 16px 28px
  );
  box-shadow: 0 1px 2px rgba(15,23,42,.18);
}
.gate-open .gate-arm {
  transform: rotate(-58deg);
}
.gate-closed .gate-arm {
  transform: rotate(0deg);
}
.gate-person {
  position: absolute;
  right: 9%;
  bottom: 13px;
  width: 18px;
  height: 30px;
}
.gate-person::before {
  content: "";
  position: absolute;
  top: 0;
  left: 6px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
}
.gate-person::after {
  content: "";
  position: absolute;
  top: 8px;
  left: 7px;
  width: 5px;
  height: 18px;
  border-radius: 3px;
  background: #64748b;
  box-shadow: -5px 8px 0 -1px #64748b, 5px 8px 0 -1px #64748b;
}
.note {font-size: 12px; color: var(--muted);}
[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
}
</style>
"""


def _init_state() -> None:
    if "turnstile" not in st.session_state:
        st.session_state.turnstile = TurnstileSimulator()
    if "history" not in st.session_state:
        st.session_state.history = []


def _run(scenario: str) -> DemoResult:
    result = run_demo(
        scenario,
        audit_path=Path("var/web_access_audit.jsonl"),
        turnstile=st.session_state.turnstile,
    )
    st.session_state.history.insert(
        0,
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "result": result,
        },
    )
    st.session_state.history = st.session_state.history[:10]
    return result


def _turnstile_label(result: DemoResult) -> str:
    if result.side_effect_allowed and result.turnstile_applied:
        return "OPEN"
    if result.side_effect_allowed and not result.turnstile_applied:
        return "OPEN · без повтора"
    return "CLOSED"


def _employee_label(result: DemoResult) -> tuple[str, str]:
    if result.employee_id:
        return f"Сотрудник {result.employee_id}", result.employee_id[-2:].upper()
    return "Личность не определена", "?"


def _render_header() -> None:
    st.html(
        """
        <div>
          <div class="page-title">Контроль доступа</div>
          <div class="page-subtitle">
            Проходная 1 · Камера 1 · локальный edge-контур
          </div>
        </div>
        """
    )


def _render_stats(last_result: DemoResult | None) -> None:
    opens = st.session_state.turnstile.open_count
    processed = len(st.session_state.history)
    reviews = sum(
        1
        for item in st.session_state.history
        if item["result"].requires_human_review
    )
    mode = "Автономный" if last_result and last_result.degraded_mode else "Штатный"

    items = (
        ("Состояние", "Система активна"),
        ("Режим", mode),
        ("Событий в сессии", str(processed)),
        ("OPEN-команд", str(opens)),
        ("На проверку", str(reviews)),
    )
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items, strict=True):
        with col:
            st.html(
                f"""
                <div class="stat-card">
                  <div class="stat-label">{label}</div>
                  <div class="stat-value">{value}</div>
                </div>
                """
            )


def _render_checks(scenario: str) -> None:
    rows = []
    for name, value, status in SCENARIO_CHECKS[scenario]:
        rows.append(
            f"""
            <div class="check-row">
              <span class="check-name">{name}</span>
              <span class="pill pill-{status}">{value}</span>
            </div>
            """
        )
    st.html(
        "<div class='panel'><div class='section-title'>Проверки</div>"
        + "".join(rows)
        + "</div>"
    )


def _render_turnstile_visual(result: DemoResult) -> None:
    is_open = result.side_effect_allowed
    state_class = "gate-open" if is_open else "gate-closed"
    badge_class = "gate-badge-open" if is_open else "gate-badge-closed"
    badge = "OPEN" if is_open else "CLOSED"
    if is_open and result.turnstile_applied:
        title = "Проход открыт"
        hint = "Команда OPEN применена к турникету."
    elif is_open:
        title = "Проход открыт"
        hint = "Повторная команда распознана: дополнительного открытия не было."
    else:
        title = "Проход закрыт"
        hint = "Автоматическое открытие для этого события запрещено."

    st.html(
        f"""
        <div class="gate-card {state_class}">
          <div class="gate-head">
            <div>
              <div class="gate-state">{title}</div>
              <div class="gate-hint">{hint}</div>
            </div>
            <span class="gate-badge {badge_class}">{badge}</span>
          </div>
          <div class="gate-scene">
            <div class="gate-lane"></div>
            <div class="gate-post gate-post-left">
              <div class="gate-light"></div>
            </div>
            <div class="gate-arm"></div>
            <div class="gate-post gate-post-right"></div>
            <div class="gate-person"></div>
          </div>
        </div>
        """
    )


def _render_event(result: DemoResult) -> None:
    decision_label, tone = DECISION_LABELS[result.decision]
    employee, avatar = _employee_label(result)
    next_action = ACTION_LABELS.get(result.next_action, result.next_action)
    if result.side_effect_allowed and not result.turnstile_applied:
        detail = "Повторная OPEN-команда распознана и не применена второй раз."
    elif result.side_effect_allowed:
        detail = "Все обязательные проверки пройдены. Турникет получил команду OPEN."
    else:
        detail = f"Турникет остаётся закрытым. Следующее действие: {next_action}."

    st.html(
        f"""
        <div class="panel">
          <div class="section-title">Последнее событие</div>
          <div class="person-card">
            <div class="avatar">{avatar}</div>
            <div>
              <div class="person-name">{employee}</div>
              <div class="person-meta">
                event_id: {result.event_id} · audit_id: {result.audit_id}
              </div>
            </div>
          </div>
          <div class="result-box result-{tone}">
            <div class="result-kicker">Решение системы</div>
            <div class="result-title">{decision_label}</div>
            <div class="result-detail">{detail}</div>
          </div>
        </div>
        """
    )

    _render_turnstile_visual(result)
    st.write("")
    human = "Требуется" if result.requires_human_review else "Не требуется"
    st.html(
        f"""
        <div class="stat-card">
          <div class="stat-label">Ручная проверка</div>
          <div class="turnstile">{human}</div>
        </div>
        """
    )


def _render_history() -> None:
    st.markdown("### Журнал проходов")
    if not st.session_state.history:
        st.caption("События появятся после первого прохода.")
        return

    rows = []
    for item in st.session_state.history:
        result = item["result"]
        decision = DECISION_LABELS[result.decision][0]
        rows.append(
            {
                "Время": item["time"],
                "Событие": result.event_id,
                "Сотрудник": result.employee_id or "—",
                "Решение": decision,
                "Турникет": _turnstile_label(result),
                "Проверка": "Да" if result.requires_human_review else "Нет",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_sidebar() -> tuple[str, bool]:
    with st.sidebar:
        st.html(
            """
            <div class="product-brand">FacePass</div>
            <div class="product-subtitle">Панель контроля доступа</div>
            <div class="sidebar-status">
              <span class="status-dot"></span>
              Edge-узел доступен
            </div>
            """
        )
        st.divider()
        st.markdown("**Точка доступа**")
        st.caption("Проходная 1")
        st.caption("Камера 1")
        st.divider()
        st.markdown("**Демо-управление**")
        selected = st.selectbox(
            "Событие",
            tuple(SCENARIOS),
            label_visibility="collapsed",
        )
        clicked = st.button(
            "Смоделировать проход",
            type="primary",
            use_container_width=True,
        )
        st.caption(
            "Сценарии используют синтетические сигналы и не содержат "
            "реальных биометрических данных."
        )
    return SCENARIOS[selected], clicked


def main() -> None:
    st.set_page_config(
        page_title="FacePass · Контроль доступа",
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html(CSS)
    _init_state()

    scenario, clicked = _render_sidebar()
    if clicked:
        st.session_state.last_result = _run(scenario)
        st.session_state.last_scenario = scenario

    last_result = st.session_state.get("last_result")
    current_scenario = st.session_state.get("last_scenario", scenario)

    _render_header()
    st.write("")
    _render_stats(last_result)
    st.write("")

    if last_result is None:
        st.html(
            """
            <div class="panel">
              <div class="section-title">Ожидание события</div>
              <div class="note">
                Выберите событие в панели слева и смоделируйте проход.
              </div>
            </div>
            """
        )
    else:
        left, right = st.columns([1.6, 1], gap="large")
        with left:
            _render_event(last_result)
        with right:
            _render_checks(current_scenario)

    st.write("")
    _render_history()
    st.caption(
        "Демо-режим: CV/PAD/ANN представлены детерминированными "
        "синтетическими сигналами."
    )


if __name__ == "__main__":
    main()
