"""
Reddit Comment Annotation Tool — Streamlit
"""
import html as _html
import datetime
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Paths ─────────────────────────────────────────────────────────────
BASE             = Path(__file__).parent
SAMPLE_PATH      = BASE / "data/annotation/sample_2450.csv"
TRAINING_PATH    = BASE / "data/annotation/training_sample.csv"
ANNOTATIONS_PATH = BASE / "data/annotation/annotations.csv"
TIME_LOG_PATH    = BASE / "data/annotation/time_log.csv"

# ── Constants ─────────────────────────────────────────────────────────
BADGE_COLORS = {
    "energy":      "#e67e22",
    "geopolitics": "#8e44ad",
    "worldnews":   "#2980b9",
    "science":     "#27ae60",
    "technology":  "#16a085",
    "economics":   "#f39c12",
    "politics":    "#e74c3c",
}
MAX_SECS     = 300
PAY_PER_HOUR = 40  # CNY — kept for time-log calculations, not shown in main UI

# [Change 11] "note" added to schema
ANNOTATION_COLS = [
    "comment_id", "subreddit", "body", "score",
    "interactivity", "is_liberal", "is_conservative",
    "rationality", "incivility", "is_uncertain", "note",
    "annotator_id", "timestamp", "time_spent_seconds",
]

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Reddit 评论标注工具",
    layout="wide",
    page_icon="✏️",
    initial_sidebar_state="expanded",
)
ss = st.session_state

# ── Helpers ───────────────────────────────────────────────────────────
def esc(text: str) -> str:
    return _html.escape(str(text)).replace("\n", "<br>")


def card(html_body: str) -> str:
    # [Change 3] font-size raised to 20px
    return (
        '<div style="background:#fff;padding:18px;border-radius:10px;'
        'border:1px solid #ddd;line-height:1.75;font-size:20px">'
        + html_body + "</div>"
    )


@st.cache_data
def load_csv(path_str: str) -> pd.DataFrame:
    return pd.read_csv(path_str, dtype=str)


def get_annotations() -> pd.DataFrame:
    if ANNOTATIONS_PATH.exists():
        return pd.read_csv(ANNOTATIONS_PATH, dtype=str)
    return pd.DataFrame(columns=ANNOTATION_COLS)


def write_annotation(d: dict) -> None:
    ann = get_annotations()
    ann = ann[
        ~((ann["comment_id"] == d["comment_id"]) &
          (ann["annotator_id"] == d["annotator_id"]))
    ]
    ann = pd.concat([ann, pd.DataFrame([d])], ignore_index=True)
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ann.to_csv(ANNOTATIONS_PATH, index=False)


def log_time(annotator_id: str, n_comments: int, seconds: float) -> None:
    today = datetime.date.today().isoformat()
    if TIME_LOG_PATH.exists():
        tl = pd.read_csv(TIME_LOG_PATH, dtype=str)
    else:
        tl = pd.DataFrame(columns=[
            "annotator_id", "session_date", "total_comments",
            "total_seconds", "estimated_pay_cny",
        ])
    mask = (tl["annotator_id"] == annotator_id) & (tl["session_date"] == today)
    if mask.any():
        i  = tl[mask].index[0]
        nc = int(tl.at[i, "total_comments"]) + n_comments
        ns = int(float(tl.at[i, "total_seconds"])) + int(seconds)
        tl.at[i, "total_comments"]    = str(nc)
        tl.at[i, "total_seconds"]     = str(ns)
        tl.at[i, "estimated_pay_cny"] = f"{ns / 3600 * PAY_PER_HOUR:.2f}"
    else:
        ns = int(seconds)
        tl = pd.concat([tl, pd.DataFrame([{
            "annotator_id":      annotator_id,
            "session_date":      today,
            "total_comments":    str(n_comments),
            "total_seconds":     str(ns),
            "estimated_pay_cny": f"{ns / 3600 * PAY_PER_HOUR:.2f}",
        }])], ignore_index=True)
    TIME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tl.to_csv(TIME_LOG_PATH, index=False)


# ══════════════════════════════════════════════════════════════════════
# SETUP SCREEN
# ══════════════════════════════════════════════════════════════════════
if not ss.get("setup_done"):
    st.title("✏️ Reddit 评论标注工具")
    st.markdown("---")

    with st.form("setup_form"):
        c1, c2 = st.columns(2)
        with c1:
            # [Change 1] Plain text input, no dropdown
            aid_input = st.text_input("编码员姓名：")
        with c2:
            mode_sel = st.radio("工作模式", [
                "🎓 练习题模式（培训用）",
                "✏️ 正式标注模式",
            ])
        go = st.form_submit_button("▶ 开始标注", use_container_width=True)

    if go:
        # [Change 1] Use aid_input directly
        aid  = aid_input.strip()
        mode = "practice" if "练习" in mode_sel else "formal"

        if not aid:
            st.error("请填写编码员姓名")
            st.stop()

        fpath = TRAINING_PATH if mode == "practice" else SAMPLE_PATH
        if not fpath.exists():
            st.error(f"找不到文件：{fpath}")
            st.stop()

        df   = load_csv(str(fpath)).copy()
        todo = df["comment_id"].tolist()

        if mode == "formal":
            ann  = get_annotations()
            done = set(ann[ann["annotator_id"] == aid]["comment_id"].tolist())
            todo = [cid for cid in todo if cid not in done]

        ss.update(dict(
            setup_done=True,
            annotator_id=aid,
            mode=mode,
            df=df,
            todo_ids=todo,
            pos=0,
            history=[],
            start_time=time.time(),
            session_start=time.time(),
            session_done=0,
            practice_submitted=False,
            practice_answers={},
            counted_ids=set(),
            p_correct=0,
            p_dims=0,
        ))
        st.rerun()

    st.stop()


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"### 👤 {ss.annotator_id}")
    st.caption("🎓 练习题模式" if ss.mode == "practice" else "✏️ 正式标注模式")
    st.divider()

    tab_rel, tab_time = st.tabs(["📊 查看信度", "⏱ 工时统计"])

    with tab_rel:
        ann_all = get_annotations()
        if ann_all.empty:
            st.info("暂无标注数据")
        else:
            coders = ann_all["annotator_id"].unique().tolist()
            if len(coders) < 2:
                st.info("需要两位编码员才能计算信度")
            else:
                a, b = coders[0], coders[1]
                a1 = ann_all[ann_all["annotator_id"] == a].set_index("comment_id")
                a2 = ann_all[ann_all["annotator_id"] == b].set_index("comment_id")
                common = a1.index.intersection(a2.index)
                st.metric("共同标注条目数", len(common))

                if len(common) >= 2:
                    st.markdown(f"*{a}* vs *{b}*")
                    for col, label in [
                        ("interactivity",   "互动性"),
                        ("rationality",     "论理性"),
                        ("incivility",      "文明性"),
                        ("is_liberal",      "自由派"),
                        ("is_conservative", "保守派"),
                    ]:
                        v1 = a1.loc[common, col].fillna("-").tolist()
                        v2 = a2.loc[common, col].fillna("-").tolist()
                        pct = sum(x == y for x, y in zip(v1, v2)) / len(common) * 100
                        try:
                            from sklearn.metrics import cohen_kappa_score
                            kappa = cohen_kappa_score(v1, v2)
                            st.write(f"**{label}** κ={kappa:.2f}  ({pct:.0f}% 一致)")
                        except Exception:
                            st.write(f"**{label}** {pct:.0f}% 一致")

                if "is_uncertain" in ann_all.columns:
                    unc = ann_all[ann_all["is_uncertain"] == "1"]
                    if not unc.empty:
                        st.divider()
                        st.write(f"🚩 存疑条目：**{len(unc)}**")
                        show_cols = [c for c in [
                            "comment_id", "annotator_id", "body",
                            "interactivity", "rationality", "incivility", "note",
                        ] if c in unc.columns]
                        with st.expander("查看存疑列表"):
                            st.dataframe(unc[show_cols], use_container_width=True)
                        st.download_button(
                            "📥 导出存疑CSV", unc.to_csv(index=False),
                            "uncertain.csv", key="dl_unc", mime="text/csv",
                        )

    with tab_time:
        if TIME_LOG_PATH.exists():
            tl = pd.read_csv(TIME_LOG_PATH)
            tl["total_seconds"] = pd.to_numeric(
                tl["total_seconds"], errors="coerce").fillna(0)
            tl["total_comments"] = pd.to_numeric(
                tl["total_comments"], errors="coerce").fillna(0)
            tl["工时"] = tl["total_seconds"].apply(
                lambda s: f"{int(s)//3600}h {int(s)%3600//60:02d}m")
            tl["均耗时(秒/条)"] = (
                tl["total_seconds"] / tl["total_comments"].replace(0, 1)
            ).round(1)
            disp = [c for c in [
                "annotator_id", "session_date", "total_comments",
                "工时", "estimated_pay_cny", "均耗时(秒/条)",
            ] if c in tl.columns]
            st.dataframe(tl[disp], use_container_width=True)
            st.download_button(
                "📥 导出CSV", tl.to_csv(index=False),
                "time_log.csv", key="dl_time", mime="text/csv",
            )
        else:
            st.info("暂无工时记录")

    st.divider()
    if st.button("🔄 重新开始"):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
# DONE SCREEN
# ══════════════════════════════════════════════════════════════════════
if ss.pos >= len(ss.todo_ids):
    st.success("🎉 所有评论标注完成！感谢您的工作。")
    st.balloons()
    st.stop()


# ══════════════════════════════════════════════════════════════════════
# CURRENT ITEM
# ══════════════════════════════════════════════════════════════════════
cid     = ss.todo_ids[ss.pos]
row     = ss.df[ss.df["comment_id"] == cid].iloc[0]
total   = len(ss.todo_ids)
body    = str(row.get("body", ""))
sub     = str(row.get("subreddit", ""))
score_s = str(row.get("score", "0"))
try:
    score_f = float(score_s)
except ValueError:
    score_f = 0.0

locked = (ss.mode == "practice") and ss.practice_submitted
k = cid  # widget key prefix

# [Change 4] Sticky CSS for left column
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] > div:first-child {
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: 100vh;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════════════════════
left, right = st.columns([3, 2], gap="large")

# ── LEFT: comment display ─────────────────────────────────────────────
with left:
    st.progress(ss.pos / total if total else 0)
    st.caption(f"已标注 **{ss.pos}** / {total} 条")

    badge_color = BADGE_COLORS.get(sub.lower(), "#888888")
    st.markdown(
        f'<span style="background:{badge_color};color:#fff;padding:4px 14px;'
        f'border-radius:999px;font-size:13px;font-weight:600">r/{sub}</span>'
        f'&nbsp;&nbsp;<span style="color:#aaa;font-size:12px">#{cid}</span>',
        unsafe_allow_html=True,
    )
    st.write("")

    if score_f < 0:
        st.markdown(
            f'<span style="color:#e74c3c;font-weight:600">得分: {int(score_f)}</span>'
            f'&nbsp;&nbsp;⚠️ <span style="color:#e74c3c;font-size:13px">'
            f'负分评论，注意文明性维度</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"得分: **{int(score_f)}**")

    st.write("")

    # [Change 3] Body card with 20px font
    body_escaped = esc(body)
    if len(body) > 300:
        st.markdown(card(esc(body[:300]) + " …"), unsafe_allow_html=True)
        with st.expander("📄 展开全文"):
            st.markdown(card(body_escaped), unsafe_allow_html=True)
    else:
        st.markdown(card(body_escaped), unsafe_allow_html=True)

    st.write("")

    # [Change 2] Timer only — no pay amount
    sess_elapsed = time.time() - ss.session_start
    st.caption(f"本次会话已工作：**{int(sess_elapsed / 60)}** 分钟")


# ── RIGHT: annotation widgets ─────────────────────────────────────────
with right:

    # ① Interactivity ──────────────────────────────────────────────────
    # [Change 5] Expander title serves as dimension label; radio label hidden
    # [Change 6] Each option on its own line
    with st.expander("📖 互动性 Interactivity — 查看定义"):
        st.markdown(
            "**1** = 评论明确回应、引用或反驳他人具体观点；含 @mention 也视为有互动性  \n"
            "**0** = 仅表达个人意见，未回应任何他人具体论点  \n"
            "**－** = 评论过短或无法判断  \n\n"
            "> 示例 1：*\"No one's stopping you, because...\"*  \n"
            "> 示例 0：*\"Climate change is real, we must act.\"*"
        )
    inter = st.radio(
        "互动性", ["1", "0", "－"], key=f"inter_{k}",
        horizontal=True, disabled=locked, label_visibility="collapsed",
    )

    st.divider()

    # ② Diversity ──────────────────────────────────────────────────────
    # [Change 5] Removed st.markdown("② 多样性 Diversity") title line
    # [Change 7] Updated definition to Stolwijk et al. (2025)
    # [Change 6] Each option on its own line
    with st.expander("📖 多样性 Diversity — 查看定义"):
        st.markdown(
            "评论的意识形态方向分为以下几类：  \n\n"
            "· 无意识形态方向（缺乏政治观点）→ is_liberal=0, is_conservative=0  \n"
            "· 自由派/民主党倾向 → is_liberal=1  \n"
            "· 保守派/共和党倾向 → is_conservative=1  \n"
            "· 中立（同时批评或支持两方）→ is_liberal=0, is_conservative=0  \n"
            "· 方向不明 → is_liberal=0, is_conservative=0  \n\n"
            "注：两个变量独立编码，极少数情况可同时为 1（评论明确包含两种立场）"
        )
    is_lib = st.checkbox("自由派立场 (is_liberal)",      key=f"lib_{k}", disabled=locked)
    is_con = st.checkbox("保守派立场 (is_conservative)", key=f"con_{k}", disabled=locked)

    st.divider()

    # ③ Rationality ────────────────────────────────────────────────────
    # [Change 5] Radio label hidden
    # [Change 6] Each option on its own line
    # [Change 8] English logical connectors
    with st.expander("📖 论理性 Rationality — 查看定义"):
        st.markdown(
            "**1** = 满足任一：  \n"
            "　① 显性推理论证（含 \"because\" \"therefore\" \"since\" 等逻辑连词）  \n"
            "　② 分析议题背景或提供背景信息  \n"
            "　③ 引用外部证据（数据、研究、链接）  \n"
            "**0** = 仅表达情绪或立场，无论证过程  \n"
            "**－** = 评论过短或无法判断  \n\n"
            "> 示例 1：*\"Costs fell 90% because of economies of scale.\"*  \n"
            "> 示例 0：*\"This policy is ridiculous and will ruin everything.\"*"
        )
    rat = st.radio(
        "论理性", ["1", "0", "－"], key=f"rat_{k}",
        horizontal=True, disabled=locked, label_visibility="collapsed",
    )

    st.divider()

    # ④ Incivility ─────────────────────────────────────────────────────
    # [Change 5] Radio label hidden
    # [Change 6] Each option on its own line
    with st.expander("📖 文明性 Incivility — 查看定义（1=不文明，0=文明）"):
        st.markdown(
            "以下**任一**出现即编为 **1**（只标注显性表达）：  \n\n"
            "① 人身攻击/辱骂　② 粗俗语言/脏话　③ 质疑他人智力或能力  \n"
            "④ 全大写喊叫　⑤ 讽刺/嘲弄　⑥ 攻击他人声誉  \n"
            "⑦ 威胁个人权利　⑧ 歧视性语言　⑨ 煽动暴力  \n\n"
            "**0** = 文明表达  \n"
            "**－** = 无法判断"
        )
    incv = st.radio(
        "文明性", ["1", "0", "－"], key=f"incv_{k}",
        horizontal=True, disabled=locked, label_visibility="collapsed",
    )

    st.write("")

    # ── Action buttons & note ──────────────────────────────────────────
    def time_spent() -> int:
        return int(min(time.time() - ss.start_time, MAX_SECS))

    def make_ann(uncertain: bool = False) -> dict:
        # [Change 11] Read note from session state via widget key
        note_val = ss.get(f"note_{k}", "")
        return {
            "comment_id":         cid,
            "subreddit":          sub,
            "body":               body,
            "score":              score_s,
            "interactivity":      inter,
            "is_liberal":         "1" if is_lib else "0",
            "is_conservative":    "1" if is_con else "0",
            "rationality":        rat,
            "incivility":         incv,
            "is_uncertain":       "1" if uncertain else "0",
            "note":               note_val,
            "annotator_id":       ss.annotator_id,
            "timestamp":          datetime.datetime.now().isoformat(),
            "time_spent_seconds": str(time_spent()),
        }

    def advance(save: bool = True, uncertain: bool = False) -> None:
        ts = time_spent()
        if save and ss.mode == "formal":
            write_annotation(make_ann(uncertain=uncertain))
            log_time(ss.annotator_id, 1, ts)
        ss.history.append(ss.pos)
        ss.pos               += 1
        ss.session_done      += 1
        ss.start_time         = time.time()
        ss.practice_submitted = False
        ss.practice_answers   = {}
        st.rerun()

    # [Change 9] Button order: 🚩 | ✅ | ⬅  (3 columns)
    # [Change 10] ⏭ 跳过 removed
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("🚩 标记存疑", use_container_width=True, key=f"flag_{k}"):
            advance(save=True, uncertain=True)

    with b2:
        if st.button("✅ 保存并继续", use_container_width=True, key=f"save_{k}"):
            if ss.mode == "practice" and not ss.practice_submitted:
                ss.practice_answers   = make_ann()
                ss.practice_submitted = True
                st.rerun()
            else:
                advance(save=True)

    with b3:
        if st.button(
            "⬅ 上一条", use_container_width=True, key=f"back_{k}",
            disabled=(len(ss.history) == 0),
        ):
            ss.pos               = ss.history.pop()
            ss.start_time        = time.time()
            ss.practice_submitted = False
            ss.practice_answers   = {}
            st.rerun()

    # [Change 11] Note text_area below buttons
    st.text_area(
        "存疑备注（选填）：",
        placeholder="记录存疑原因，方便后续讨论",
        height=80,
        key=f"note_{k}",
    )


# ══════════════════════════════════════════════════════════════════════
# PRACTICE MODE: answer comparison
# ══════════════════════════════════════════════════════════════════════
if ss.mode == "practice" and ss.practice_submitted and ss.practice_answers:
    ref = ss.df[ss.df["comment_id"] == cid].iloc[0]
    st.divider()
    st.subheader("📋 答案对比")

    CHECK = [
        ("interactivity",   "互动性"),
        ("is_liberal",      "自由派立场"),
        ("is_conservative", "保守派立场"),
        ("rationality",     "论理性"),
        ("incivility",      "文明性"),
    ]

    n_correct = 0
    for col, label in CHECK:
        user_v = str(ss.practice_answers.get(col, "")).strip()
        ref_v  = str(ref.get(col, "")).strip()
        ok     = user_v == ref_v
        if ok:
            n_correct += 1
        icon = "✅" if ok else "❌"
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{label}**")
        c2.write(f"你: `{user_v}`")
        c3.write(f"参考: `{ref_v}`")
        c4.write(icon)

    if cid not in ss.counted_ids:
        ss.p_correct += n_correct
        ss.p_dims    += len(CHECK)
        ss.counted_ids.add(cid)

    this_acc    = n_correct / len(CHECK) * 100
    overall_acc = ss.p_correct / ss.p_dims * 100 if ss.p_dims else 0

    ca, cb = st.columns(2)
    ca.info(f"本题准确率：**{this_acc:.0f}%** （{n_correct}/{len(CHECK)}）")
    cb.success(f"累计准确率：**{overall_acc:.1f}%**")

    if st.button("➡ 下一题", key=f"next_{k}"):
        advance(save=False)
