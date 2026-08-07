import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Банк «ЦифраФинанс»",
    page_icon="🏦",
    layout="wide"
)

# ============================
# CSS
# ============================

st.markdown("""
<style>

.stApp{
    background:#f4f6fa;
}

.block-container{
    padding-top:1rem;
    padding-bottom:1rem;
}

h1{
    color:#153B66;
    font-size:34px;
    font-weight:700;
}

div[data-testid="metric-container"]{
    background:white;
    border-radius:16px;
    padding:16px;
    box-shadow:0 4px 18px rgba(0,0,0,.08);
    border-left:6px solid #153B66;
}

div[data-testid="metric-container"] label{
    font-size:14px;
}

section[data-testid="stSidebar"]{
    background:#153B66;
}

section[data-testid="stSidebar"] *{
    color:white;
}

thead tr th{
    background:#153B66 !important;
    color:white !important;
}

footer{
    visibility:hidden;
}

header{
    visibility:hidden;
}

</style>
""", unsafe_allow_html=True)
# ============================
# DATA
# ============================
from pathlib import Path

@st.cache_data
def load_data():

    base_path = Path(__file__).parent

    df = pd.read_csv(base_path / "loan_portfolio_clean.csv")
    branch = pd.read_csv(base_path / "branch_reference.csv")

    df["issue_date"] = pd.to_datetime(df["issue_date"])
    df["Quarter"] = df["issue_date"].dt.to_period("Q").astype(str)

    return df, branch

# ============================
# SIDEBAR
# ============================

st.sidebar.title("Фильтры")

regions=st.sidebar.multiselect(
    "Регион",
    sorted(df.region.unique()),
    default=sorted(df.region.unique())
)

channels=st.sidebar.multiselect(
    "Канал",
    sorted(df.channel.unique()),
    default=sorted(df.channel.unique())
)

products=st.sidebar.multiselect(
    "Продукт",
    sorted(df.loan_product.unique()),
    default=sorted(df.loan_product.unique())
)

quarters=st.sidebar.multiselect(
    "Период",
    sorted(df.Quarter.unique()),
    default=sorted(df.Quarter.unique())
)

filtered=df[
    (df.region.isin(regions))&
    (df.channel.isin(channels))&
    (df.loan_product.isin(products))&
    (df.Quarter.isin(quarters))
].copy()

# ============================
# EXPECTED LOSS
# ============================

filtered["LGD"]=np.select(
    [
        filtered.credit_score>=680,
        filtered.credit_score>=600
    ],
    [
        0.4,
        0.5
    ],
    default=0.6
)

filtered["PD"]=filtered.groupby("LGD")["is_default"].transform("mean")

filtered["EL"]=(
    filtered.loan_amount*
    filtered.PD*
    filtered.LGD
)

portfolio=filtered.loan_amount.sum()

dr=filtered.is_default.mean()

el=filtered.EL.sum()

avg_dti=filtered.dti_ratio.mean()

st.title("Дашборд мониторинга кредитного портфеля")
st.caption("Еженедельный мониторинг ключевых показателей розничного кредитного портфеля")

# =====================================================
# KPI
# =====================================================

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="Объем кредитного портфеля",
        value=f"{portfolio/1e9:.2f} млрд ₽"
    )

with kpi2:
    delta = dr - 0.10

    st.metric(
        label="Уровень дефолтов",
        value=f"{dr:.2%}"
    )

with kpi3:
    st.metric(
        label="Ожидаемые кредитные потери",
        value=f"{el/1e6:.1f} млн ₽"
    )

with kpi4:
    st.metric(
        label="Средний DTI",
        value=f"{avg_dti:.1f}%"
    )

st.divider()
st.markdown("---")

# =====================================================
# Quarterly Dynamics
# =====================================================

quarter = (
    filtered
    .groupby("Quarter")
    .agg(
        Loans=("loan_id", "count"),
        DefaultRate=("is_default", "mean")
    )
    .reset_index()
)

fig = go.Figure()

fig.add_trace(
    go.Bar(
        x=quarter["Quarter"],
        y=quarter["Loans"],
        name="Количество кредитов",
        marker_color="#355C7D"
    )
)

fig.add_trace(
    go.Scatter(
        x=quarter["Quarter"],
        y=quarter["DefaultRate"] * 100,
        mode="lines+markers",
        name="Уровень дефолтов",
        line=dict(color="#C06C84", width=4),
        yaxis="y2"
    )
)

fig.update_layout(

    template="plotly_white",

    title="Динамика выдач кредитов и уровня дефолтов по кварталам",

    height=470,

    hovermode="x unified",

    legend=dict(
        orientation="h",
        y=1.1
    ),

    yaxis=dict(
        title="Количество кредитов"
    ),

    yaxis2=dict(
        title="Уровень дефолтов (%)",
        overlaying="y",
        side="right"
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()

c1, c2, c3 = st.columns(3)

with c1:
    st.info(
        f"Кредитов в выборке: {len(filtered):,}"
    )

with c2:
    st.info(
        f"Средний скоринг: {filtered.credit_score.mean():.1f}"
    )

with c3:
    st.info(
        f"Средний доход: {filtered.monthly_income.mean():,.0f} ₽"
    )

st.markdown("---")

# =====================================================
# Scatter
# =====================================================

st.subheader("Зависимость кредитного рейтинга и долговой нагрузки")

plot_df = filtered.copy()

plot_df["Статус кредита"] = plot_df["is_default"].map({
    0: "Без дефолта",
    1: "Дефолт"
})

scatter = px.scatter(
    plot_df,
    x="credit_score",
    y="dti_ratio",
    color="Статус кредита",
    color_discrete_map={
        "Без дефолта": "#4C78A8",
        "Дефолт": "#D1495B"
    },
    opacity=0.45,
    labels={
        "credit_score": "Кредитный рейтинг",
        "dti_ratio": "DTI (%)"
    },
    hover_data={
        "loan_amount": ":,.0f",
        "monthly_income": ":,.0f",
        "interest_rate": ":.1f",
        "credit_score": True,
        "dti_ratio": True
    },
    template="plotly_white"
)

scatter.update_traces(
    marker=dict(
        size=5,
        line=dict(width=0)
    )
)


scatter.update_layout(
    title="Связь кредитного рейтинга и DTI",
    legend_title="Статус кредита",
    xaxis_title="Кредитный рейтинг",
    yaxis_title="DTI (%)",
    height=600,
    margin=dict(l=20, r=20, t=60, b=20)
)

st.plotly_chart(scatter, use_container_width=True)
# =====================================================
# Heatmap
# =====================================================

left, right = st.columns([1.1, 1.2])

with left:

    heat = (
        filtered
        .groupby(["employment_type", "channel"])["is_default"]
        .mean()
        .reset_index()
    )

    heat = heat.pivot(
        index="employment_type",
        columns="channel",
        values="is_default"
    )

    fig_heat = px.imshow(

        heat * 100,

        text_auto=".1f",

        color_continuous_scale="YlOrRd",

        aspect="auto",

        labels=dict(
            color="Уровень дефолтов (%)"
        ),

        title="Уровень дефолтов по типу занятости и каналу выдачи"
    )

    fig_heat.update_layout(

        template="plotly_white",

        height=500,

        margin=dict(
            l=20,
            r=20,
            t=50,
            b=20
        )
    )

    st.plotly_chart(
        fig_heat,
        use_container_width=True
    )

# =====================================================
# Plan vs Target
# =====================================================

with right:

    fact = (

        filtered

        .groupby(["region", "channel"])

        .agg(

            fact_default_rate=("is_default", "mean"),

            fact_credit_score=("credit_score", "mean"),

            fact_dti=("dti_ratio", "mean")

        )

        .reset_index()

    )

    plan = branch.rename(

        columns={

            "target_default_rate": "plan_default_rate",

            "target_avg_credit_score": "plan_credit_score",

            "target_avg_dti": "plan_dti"

        }

    )

    plan_fact = fact.merge(

        plan[[
            "region",
            "channel",
            "plan_default_rate",
            "plan_credit_score",
            "plan_dti"
        ]],

        how="left",

        on=["region", "channel"]

    )

    plan_fact["DR Δ"] = (
        plan_fact["fact_default_rate"] -
        plan_fact["plan_default_rate"]
    ) * 100

    plan_fact["Score Δ"] = (
        plan_fact["fact_credit_score"] -
        plan_fact["plan_credit_score"]
    )

    plan_fact["DTI Δ"] = (
        plan_fact["fact_dti"] -
        plan_fact["plan_dti"]
    )

    show = plan_fact[[
        "region",
        "channel",
        "fact_default_rate",
        "plan_default_rate",
        "DR Δ",
        "fact_credit_score",
        "plan_credit_score",
        "Score Δ",
        "fact_dti",
        "plan_dti",
        "DTI Δ"
    ]].copy()

    show["fact_default_rate"] *= 100
    show["plan_default_rate"] *= 100

    st.subheader("План-факт анализ по филиалам")

    st.dataframe(

        show.style

        .background_gradient(

            subset=["DR Δ"],

            cmap="RdYlGn_r"

        )

        .background_gradient(

            subset=["Score Δ"],

            cmap="RdYlGn"

        )

        .background_gradient(

            subset=["DTI Δ"],

            cmap="RdYlGn_r"

        )

        .format({

            "fact_default_rate": "{:.2f}",

            "plan_default_rate": "{:.2f}",

            "DR Δ": "{:.2f}",

            "fact_credit_score": "{:.1f}",

            "plan_credit_score": "{:.1f}",

            "Score Δ": "{:.1f}",

            "fact_dti": "{:.1f}",

            "plan_dti": "{:.1f}",

            "DTI Δ": "{:.1f}"

        }),

        use_container_width=True,

        height=500

    )

st.markdown("---")

c1, c2 = st.columns([4,1])

with c1:

    st.caption(
        """
Используйте фильтры слева для анализа отдельных регионов, каналов продаж и кредитных продуктов.

        """
    )

