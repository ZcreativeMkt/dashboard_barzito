from pathlib import Path
import pandas as pd
from dash import Dash, dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
ARQUIVO = BASE_DIR / "data" / "BARZITO_DADOS_GERAL.xlsx"
TOP_N_DEFAULT = 15
PORT = 8050
HOST = "0.0.0.0"

MESES_ORDEM = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
MAPA_MES_NUM = {mes: i + 1 for i, mes in enumerate(MESES_ORDEM)}


def carregar_dados(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}\n"
            "Coloque BARZITO_DADOS_GERAL.xlsx dentro da pasta data/."
        )

    df = pd.read_excel(caminho)

    colunas_esperadas = {"ano", "mes", "subgrupo", "produto", "valor", "quantidade"}
    faltantes = colunas_esperadas - set(df.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes no arquivo: {sorted(faltantes)}")

    df = df.copy()
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df["mes"] = df["mes"].astype(str).str.strip()
    df["subgrupo"] = df["subgrupo"].astype(str).str.strip().str.upper()
    df["produto"] = df["produto"].astype(str).str.strip().str.upper()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0)
    df["mes_num"] = df["mes"].map(MAPA_MES_NUM)
    df = df.dropna(subset=["ano", "mes_num"])
    df["ano"] = df["ano"].astype(int)
    return df


df_base = carregar_dados(ARQUIVO)
anos_disponiveis = sorted(df_base["ano"].dropna().unique().tolist())
categorias_disponiveis = sorted(df_base["subgrupo"].dropna().unique().tolist())
produtos_disponiveis = sorted(df_base["produto"].dropna().unique().tolist())


def filtrar_dados(df: pd.DataFrame, anos=None, meses=None, categorias=None, produtos=None) -> pd.DataFrame:
    out = df.copy()
    if anos:
        out = out[out["ano"].isin(anos)]
    if meses:
        out = out[out["mes"].isin(meses)]
    if categorias:
        out = out[out["subgrupo"].isin(categorias)]
    if produtos:
        out = out[out["produto"].isin(produtos)]
    return out


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def kpi_card(titulo: str, valor: str, subtitulo: str = ""):
    return html.Div(
        [
            html.Div(titulo, style={"fontSize": "14px", "color": "#94a3b8", "marginBottom": "8px"}),
            html.Div(valor, style={"fontSize": "28px", "fontWeight": "700", "color": "#f8fafc"}),
            html.Div(subtitulo, style={"fontSize": "12px", "color": "#64748b", "marginTop": "6px"}),
        ],
        style={
            "background": "#0f172a",
            "border": "1px solid #1e293b",
            "borderRadius": "16px",
            "padding": "18px",
            "boxShadow": "0 8px 20px rgba(0,0,0,0.18)",
        },
    )


def card_grafico(titulo: str, graph_id: str):
    return html.Div(
        [
            html.H3(titulo, style={"margin": "0 0 12px 0", "fontSize": "18px", "color": "#e2e8f0"}),
            dcc.Graph(id=graph_id, config={"displaylogo": False}),
        ],
        style={
            "background": "#0f172a",
            "border": "1px solid #1e293b",
            "borderRadius": "18px",
            "padding": "18px",
            "boxShadow": "0 8px 20px rgba(0,0,0,0.18)",
        },
    )


def figura_vazia(titulo: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=titulo,
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(text="Sem dados para os filtros selecionados", showarrow=False, font=dict(size=16))],
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def aplicar_layout(fig: go.Figure, altura: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=60, b=20),
        height=altura,
    )
    return fig


def tabela_produtos(df: pd.DataFrame, top_n: int, criterio: str) -> pd.DataFrame:
    agg = (
        df.groupby(["produto", "subgrupo"], as_index=False)
        .agg(valor=("valor", "sum"), quantidade=("quantidade", "sum"))
    )
    agg["preco_medio"] = agg.apply(
        lambda r: (r["valor"] / r["quantidade"]) if r["quantidade"] else 0,
        axis=1,
    )

    asc = criterio == "menos"
    agg = agg.sort_values(["quantidade", "valor"], ascending=[asc, asc]).head(top_n)
    return agg


app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "BI Barzito"

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("BI Restaurante · Barzito", style={"margin": "0", "color": "#f8fafc"}),
                html.Div(
                    "Dashboard interativo para cruzar produto, categoria, período, faturamento e volume.",
                    style={"color": "#94a3b8", "marginTop": "6px"},
                ),
            ],
            style={"marginBottom": "20px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Ano", style={"display": "block", "marginBottom": "6px", "color": "#cbd5e1"}),
                        dcc.Dropdown(
                            id="filtro_ano",
                            options=[{"label": str(a), "value": int(a)} for a in anos_disponiveis],
                            value=anos_disponiveis,
                            multi=True,
                            placeholder="Selecione o ano",
                        ),
                    ],
                    style={"minWidth": "220px", "flex": "1"},
                ),
                html.Div(
                    [
                        html.Label("Mês", style={"display": "block", "marginBottom": "6px", "color": "#cbd5e1"}),
                        dcc.Dropdown(
                            id="filtro_mes",
                            options=[{"label": m, "value": m} for m in MESES_ORDEM if m in df_base["mes"].unique()],
                            multi=True,
                            placeholder="Todos os meses",
                        ),
                    ],
                    style={"minWidth": "260px", "flex": "1.2"},
                ),
                html.Div(
                    [
                        html.Label("Categoria", style={"display": "block", "marginBottom": "6px", "color": "#cbd5e1"}),
                        dcc.Dropdown(
                            id="filtro_categoria",
                            options=[{"label": c, "value": c} for c in categorias_disponiveis],
                            multi=True,
                            placeholder="Todas as categorias",
                        ),
                    ],
                    style={"minWidth": "280px", "flex": "1.5"},
                ),
                html.Div(
                    [
                        html.Label("Produto", style={"display": "block", "marginBottom": "6px", "color": "#cbd5e1"}),
                        dcc.Dropdown(
                            id="filtro_produto",
                            options=[{"label": p, "value": p} for p in produtos_disponiveis],
                            multi=True,
                            placeholder="Todos os produtos",
                        ),
                    ],
                    style={"minWidth": "320px", "flex": "2"},
                ),
                html.Div(
                    [
                        html.Label("Top N", style={"display": "block", "marginBottom": "6px", "color": "#cbd5e1"}),
                        dcc.Input(
                            id="top_n",
                            type="number",
                            min=3,
                            max=50,
                            step=1,
                            value=TOP_N_DEFAULT,
                            style={
                                "width": "100%",
                                "padding": "10px",
                                "borderRadius": "8px",
                                "border": "1px solid #334155",
                                "background": "#020617",
                                "color": "#f8fafc",
                            },
                        ),
                    ],
                    style={"minWidth": "120px", "width": "120px"},
                ),
                html.Div(
                    [
                        html.Label("Modo ranking", style={"display": "block", "marginBottom": "6px", "color": "#cbd5e1"}),
                        dcc.RadioItems(
                            id="modo_ranking",
                            options=[
                                {"label": " Mais vendidos", "value": "mais"},
                                {"label": " Menos vendidos", "value": "menos"},
                            ],
                            value="mais",
                            inline=False,
                            labelStyle={"display": "block", "marginBottom": "4px", "color": "#e2e8f0"},
                            inputStyle={"marginRight": "6px"},
                        ),
                    ],
                    style={"minWidth": "170px", "width": "170px"},
                ),
            ],
            style={
                "display": "flex",
                "gap": "12px",
                "flexWrap": "wrap",
                "background": "#0f172a",
                "border": "1px solid #1e293b",
                "borderRadius": "18px",
                "padding": "18px",
                "marginBottom": "20px",
            },
        ),
        html.Div(
            [
                html.Div(id="kpi_faturamento", style={"flex": "1"}),
                html.Div(id="kpi_quantidade", style={"flex": "1"}),
                html.Div(id="kpi_ticket", style={"flex": "1"}),
                html.Div(id="kpi_produtos", style={"flex": "1"}),
            ],
            style={"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)", "gap": "14px", "marginBottom": "20px"},
        ),
        html.Div(
            [
                html.Div(card_grafico("Evolução mensal de faturamento", "grafico_faturamento_mensal"), style={"flex": "1.4"}),
                html.Div(card_grafico("Distribuição por categoria", "grafico_categoria_pizza"), style={"flex": "1"}),
            ],
            style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
        ),
        html.Div(
            [
                html.Div(card_grafico("Ranking de produtos", "grafico_ranking_produtos"), style={"flex": "1.3"}),
                html.Div(card_grafico("Participação por produto", "grafico_produtos_pizza"), style={"flex": "1"}),
            ],
            style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
        ),
        html.Div(
            [
                html.Div(card_grafico("Faturamento por categoria", "grafico_categoria_barras"), style={"flex": "1"}),
                html.Div(card_grafico("Top 10 produtos por mês", "grafico_top_mes"), style={"flex": "1.3"}),
            ],
            style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "14px"},
        ),
        html.Div(
            [
                html.H3("Tabela analítica de produtos", style={"margin": "0 0 12px 0", "fontSize": "18px", "color": "#e2e8f0"}),
                dash_table.DataTable(
                    id="tabela_produtos",
                    columns=[
                        {"name": "Produto", "id": "produto", "type": "text"},
                        {"name": "Categoria", "id": "subgrupo", "type": "text"},
                        {"name": "Valor", "id": "valor", "type": "numeric", "format": {"specifier": ",.2f"}},
                        {"name": "Quantidade", "id": "quantidade", "type": "numeric", "format": {"specifier": ","}},
                        {"name": "Preço Médio", "id": "preco_medio", "type": "numeric", "format": {"specifier": ",.2f"}},
                    ],
                    data=[],
                    page_size=15,
                    sort_action="native",
                    sort_mode="multi",
                    filter_action="native",
                    style_as_list_view=True,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#020617",
                        "color": "#f8fafc",
                        "fontWeight": "bold",
                        "border": "1px solid #1e293b",
                    },
                    style_cell={
                        "backgroundColor": "#0f172a",
                        "color": "#e2e8f0",
                        "border": "1px solid #1e293b",
                        "padding": "10px",
                        "textAlign": "left",
                    },
                ),
            ],
            style={
                "background": "#0f172a",
                "border": "1px solid #1e293b",
                "borderRadius": "18px",
                "padding": "18px",
                "boxShadow": "0 8px 20px rgba(0,0,0,0.18)",
            },
        ),
    ],
    style={
        "background": "#020617",
        "minHeight": "100vh",
        "padding": "22px",
        "fontFamily": "Arial, sans-serif",
    },
)


@app.callback(
    Output("kpi_faturamento", "children"),
    Output("kpi_quantidade", "children"),
    Output("kpi_ticket", "children"),
    Output("kpi_produtos", "children"),
    Output("grafico_faturamento_mensal", "figure"),
    Output("grafico_categoria_pizza", "figure"),
    Output("grafico_ranking_produtos", "figure"),
    Output("grafico_produtos_pizza", "figure"),
    Output("grafico_categoria_barras", "figure"),
    Output("grafico_top_mes", "figure"),
    Output("tabela_produtos", "data"),
    Input("filtro_ano", "value"),
    Input("filtro_mes", "value"),
    Input("filtro_categoria", "value"),
    Input("filtro_produto", "value"),
    Input("top_n", "value"),
    Input("modo_ranking", "value"),
)
def atualizar_dashboard(anos, meses, categorias, produtos, top_n, modo_ranking):
    top_n = max(3, min(int(top_n or TOP_N_DEFAULT), 50))
    df = filtrar_dados(df_base, anos, meses, categorias, produtos)

    if df.empty:
        vazio = figura_vazia("Sem dados")
        return (
            kpi_card("Faturamento", "R$ 0,00"),
            kpi_card("Itens vendidos", "0"),
            kpi_card("Preço médio por item", "R$ 0,00"),
            kpi_card("Produtos distintos", "0"),
            vazio, vazio, vazio, vazio, vazio, vazio, [],
        )

    faturamento_total = df["valor"].sum()
    quantidade_total = df["quantidade"].sum()
    ticket_medio_item = faturamento_total / quantidade_total if quantidade_total else 0
    produtos_distintos = df["produto"].nunique()
    categorias_distintas = df["subgrupo"].nunique()

    kpi1 = kpi_card("Faturamento total", formatar_moeda(faturamento_total), f"{len(df):,} registros filtrados".replace(",", "."))
    kpi2 = kpi_card("Itens vendidos", formatar_numero(quantidade_total), f"{categorias_distintas} categorias no corte")
    kpi3 = kpi_card("Preço médio por item", formatar_moeda(ticket_medio_item), "Valor ÷ quantidade")
    kpi4 = kpi_card("Produtos distintos", formatar_numero(produtos_distintos), "Mix ativo no filtro")

    mensal = (
        df.groupby(["ano", "mes", "mes_num"], as_index=False)
        .agg(valor=("valor", "sum"), quantidade=("quantidade", "sum"))
        .sort_values(["ano", "mes_num"])
    )
    mensal["periodo"] = mensal["mes"].str[:3] + "/" + mensal["ano"].astype(str)

    fig_faturamento = px.bar(
        mensal,
        x="periodo",
        y="valor",
        color="ano",
        barmode="group",
        title="Faturamento por mês",
        labels={"valor": "Faturamento", "periodo": "Período"},
    )
    aplicar_layout(fig_faturamento)

    por_categoria = (
        df.groupby("subgrupo", as_index=False)
        .agg(valor=("valor", "sum"), quantidade=("quantidade", "sum"))
        .sort_values("valor", ascending=False)
    )

    fig_categoria_pizza = px.pie(
        por_categoria,
        names="subgrupo",
        values="valor",
        title="Participação do faturamento por categoria",
        hole=0.45,
    )
    aplicar_layout(fig_categoria_pizza)

    ranking = tabela_produtos(df, top_n, modo_ranking)
    titulo_ranking = f"{'Top' if modo_ranking == 'mais' else 'Bottom'} {top_n} produtos por quantidade"
    fig_ranking = px.bar(
        ranking.sort_values("quantidade", ascending=(modo_ranking == "menos")),
        x="quantidade",
        y="produto",
        color="subgrupo",
        orientation="h",
        title=titulo_ranking,
        hover_data={"valor": ":.2f", "preco_medio": ":.2f"},
    )
    fig_ranking.update_layout(yaxis={"categoryorder": "total ascending"})
    aplicar_layout(fig_ranking, altura=520)

    fig_produtos_pizza = px.pie(
        ranking,
        names="produto",
        values="quantidade",
        title="Participação no volume vendido",
        hole=0.45,
    )
    aplicar_layout(fig_produtos_pizza)

    fig_categoria_barras = px.bar(
        por_categoria,
        x="subgrupo",
        y="valor",
        color="quantidade",
        title="Faturamento por categoria",
        hover_data={"quantidade": True, "valor": ":.2f"},
    )
    fig_categoria_barras.update_xaxes(categoryorder="total descending")
    aplicar_layout(fig_categoria_barras)

    top_mes = (
        df.groupby(["ano", "mes", "mes_num", "produto"], as_index=False)
        .agg(quantidade=("quantidade", "sum"), valor=("valor", "sum"))
        .sort_values(["ano", "mes_num", "quantidade"], ascending=[True, True, False])
    )
    top_mes = top_mes.groupby(["ano", "mes", "mes_num"], as_index=False).head(10)
    top_mes["periodo"] = top_mes["mes"].str[:3] + "/" + top_mes["ano"].astype(str)

    fig_top_mes = px.bar(
        top_mes,
        x="periodo",
        y="quantidade",
        color="produto",
        title="Top 10 produtos por mês",
        hover_data={"valor": ":.2f"},
    )
    aplicar_layout(fig_top_mes, altura=500)

    tabela = ranking[["produto", "subgrupo", "valor", "quantidade", "preco_medio"]].to_dict("records")

    return (
        kpi1,
        kpi2,
        kpi3,
        kpi4,
        fig_faturamento,
        fig_categoria_pizza,
        fig_ranking,
        fig_produtos_pizza,
        fig_categoria_barras,
        fig_top_mes,
        tabela,
    )


if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=PORT)
