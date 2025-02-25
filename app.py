import networkx as nx
from ipysigma import Sigma
from shinyswatch import theme
from shiny import reactive, req
from shiny.express import input, ui, render
from shinywidgets import render_widget, render_plotly
import pandas as pd
import numpy as np
import netfunction
import plotly.express as px
from faicons import icon_svg
import plotly.graph_objects as go


ui.page_opts(
    title="Network Dashboard",
    fillable=True,
    id="page",
    theme=theme.journal
)

with ui.sidebar(width=280):
    ui.HTML("<h4>Обработка данных</h4>")
    ui.hr()
    ui.input_file("file", "Загрузить данные:", accept=".xlsx", width=250)


@reactive.calc
def df():
    f = req(input.file())
    return pd.read_excel(f[0]['datapath'])


@reactive.calc
def processed_data():
    data = df()
    data['Обработанные навыки'] = data['Ключевые навыки'].apply(
        netfunction.parse_skills)
    data = data.dropna(subset='Работодатель')
    data.reset_index(inplace=True, drop=True)
    data['Дата публикации'] = pd.to_datetime(data['Дата публикации'])
    data["Федеральный округ"] = data["Название региона"].apply(
        netfunction.get_federal_district)
    return data


@reactive.effect
def update_filter_choices():
    data = processed_data()
    exp_choices = sorted(data["Опыт работы"].dropna().unique().tolist())
    region_choices = sorted(
        data["Название региона"].dropna().unique().tolist())
    ui.update_selectize("experience", choices=exp_choices)
    ui.update_selectize("region", choices=region_choices)


@reactive.effect
def update_date_range():
    data = processed_data()
    if not data.empty:
        dates = data['Дата публикации']
        min_date = dates.min().date().isoformat()
        max_date = dates.max().date().isoformat()
        ui.update_date_range("pub_date", min=min_date,
                             max=max_date, start=min_date, end=max_date)


@reactive.effect
def update_salary_range():
    data = processed_data()
    if not data.empty:
        min_salary = int(data['Заработная плата'].min())
        max_salary = int(data['Заработная плата'].max())
        ui.update_slider("salary", min=min_salary,
                         max=max_salary, value=[min_salary, max_salary])


@reactive.calc
def filtered_data():
    data = processed_data()
    if input.pub_date():
        start_date, end_date = input.pub_date()
        data = data[(data['Дата публикации'] >= pd.to_datetime(start_date)) &
                    (data['Дата публикации'] <= pd.to_datetime(end_date))]
    if input.experience():
        data = data[data['Опыт работы'].isin(input.experience())]
    if input.region():
        data = data[data['Название региона'].isin(input.region())]
    if input.salary():
        min_salary, max_salary = input.salary()
        data = data[(data['Заработная плата'] >= min_salary) &
                    (data['Заработная плата'] <= max_salary)]
    return data


@reactive.calc
def skills_roles_matrix():
    data = filtered_data()
    if data.empty:
        return pd.DataFrame()
    return netfunction.create_group_values_matrix(data, 'Название специальности', 'Обработанные навыки')


@reactive.calc
def bipartite_graph():
    matrix = skills_roles_matrix()
    if matrix.empty:
        return None
    return netfunction.create_bipartite_graph(matrix)


@reactive.effect
def update_filter_choices_sem():
    data = processed_data()
    exp_choices = sorted(data["Опыт работы"].dropna().unique().tolist())
    region_choices = sorted(
        data["Название региона"].dropna().unique().tolist())
    specialty_choices = sorted(
        data["Название специальности"].dropna().unique().tolist())
    ui.update_selectize("experience_sem", choices=exp_choices)
    ui.update_selectize("region_sem", choices=region_choices)
    ui.update_selectize("specialty", choices=specialty_choices)


@reactive.effect
def update_date_range_sem():
    data = processed_data()
    if not data.empty:
        dates = data['Дата публикации']
        min_date = dates.min().date().isoformat()
        max_date = dates.max().date().isoformat()
        ui.update_date_range("pub_date_sem", min=min_date,
                             max=max_date, start=min_date, end=max_date)


@reactive.effect
def update_salary_range_sem():
    data = processed_data()
    if not data.empty:
        min_salary = int(data['Заработная плата'].min())
        max_salary = int(data['Заработная плата'].max())
        ui.update_slider("salary_sem", min=min_salary,
                         max=max_salary, value=[min_salary, max_salary])


@reactive.calc
def filtered_data_semantic():
    data = processed_data()
    if input.pub_date_sem():
        start_date, end_date = input.pub_date_sem()
        data = data[(data['Дата публикации'] >= pd.to_datetime(start_date)) &
                    (data['Дата публикации'] <= pd.to_datetime(end_date))]
    if input.experience_sem():
        data = data[data['Опыт работы'].isin(input.experience_sem())]
    if input.region_sem():
        data = data[data['Название региона'].isin(input.region_sem())]
    if input.salary_sem():
        min_salary, max_salary = input.salary_sem()
        data = data[(data['Заработная плата'] >= min_salary) &
                    (data['Заработная плата'] <= max_salary)]
    if input.specialty():
        data = data[data['Название специальности'].isin(input.specialty())]
    return data


@reactive.calc
def semantic_cooccurrence_matrix():
    data = filtered_data_semantic()
    if data.empty:
        return pd.DataFrame()
    return netfunction.create_co_occurrence_matrix(data, 'Обработанные навыки')


@reactive.calc
def semantic_graph():
    matrix = semantic_cooccurrence_matrix()
    if matrix.empty:
        return None
    G = nx.from_pandas_adjacency(matrix)
    return G


with ui.nav_panel("Данные", icon=icon_svg("table")):
    with ui.card(full_screen=True):
        ui.card_header("📖 Загруженные данные")

        @render.data_frame
        def table():
            return render.DataTable(processed_data(), filters=True, height='700px')


with ui.nav_panel("Визуализация", icon=icon_svg("chart-bar")):
    with ui.layout_columns(col_widths=(12, 12)):
        with ui.card(full_screen=True):
            ui.card_header(
                "💰 Распределение средней зарплаты: Федеральный округ → Специальность → Опыт работы")

            @render_plotly
            def sankey_chart():
                data = filtered_data()
                if data.empty:
                    return px.scatter(title="Нет данных для отображения")

                df_sankey = data.groupby(["Федеральный округ", "Название специальности", "Опыт работы"])[
                    "Заработная плата"].mean().reset_index()

                unique_districts = list(
                    df_sankey["Федеральный округ"].unique())
                unique_specialties = list(
                    df_sankey["Название специальности"].unique())
                unique_experience = list(df_sankey["Опыт работы"].unique())

                nodes = unique_districts + unique_specialties + unique_experience
                node_indices = {name: i for i, name in enumerate(nodes)}

                source_districts = df_sankey["Федеральный округ"].map(
                    node_indices).tolist()
                target_specialties = df_sankey["Название специальности"].map(
                    node_indices).tolist()
                values_districts = df_sankey["Заработная плата"].tolist()

                source_specialties = df_sankey["Название специальности"].map(
                    node_indices).tolist()
                target_experience = df_sankey["Опыт работы"].map(
                    node_indices).tolist()
                values_specialties = df_sankey["Заработная плата"].tolist()

                source = source_districts + source_specialties
                target = target_specialties + target_experience
                value = values_districts + values_specialties

                palette = px.colors.qualitative.Set2
                node_colors = {node: palette[i % len(
                    palette)] for i, node in enumerate(nodes)}

                opacity = 0.4
                link_colors = [node_colors[nodes[src]].replace(
                    ")", f", {opacity})").replace("rgb", "rgba") for src in source]

                fig = go.Figure(go.Sankey(
                    valueformat=".0f",
                    node=dict(
                        pad=15,
                        thickness=25,
                        line=dict(color="black", width=0.7),
                        label=nodes,
                        color=[node_colors[node]
                               for node in nodes],
                        hoverlabel=dict(
                            font=dict(size=14, family="Arial", color="black", weight="bold")),
                    ),
                    link=dict(
                        source=source,
                        target=target,
                        value=value,
                        color=link_colors
                    )
                ))

                fig.update_layout(
                    title=None,
                    font=dict(size=14, family="Arial", color="black",
                              weight="bold"),
                    plot_bgcolor="white"
                )

                return fig

        with ui.card(full_screen=True):
            ui.card_header("📈 Динамика публикации вакансий по специальностям")

            @render_plotly
            def vacancies_trend():
                data = filtered_data()
                if data.empty:
                    return px.scatter(title="Нет данных для отображения")

                df_grouped = data.groupby(
                    [pd.Grouper(key="Дата публикации", freq="M"),
                     "Название специальности"]
                ).size().reset_index(name="Количество вакансий")

                fig = px.line(
                    df_grouped,
                    x="Дата публикации",
                    y="Количество вакансий",
                    color="Название специальности",
                    title="",
                    template="plotly_white",
                    markers=True
                ).update_layout(xaxis_title=None, yaxis_title=None, title=None)
                return fig


with ui.nav_panel("Сеть", icon=icon_svg('circle-nodes')):
    with ui.navset_card_underline(id="selected_navset_card_underline1"):
        with ui.nav_panel("Двумодальный граф"):
            with ui.layout_columns(col_widths=(3, 9)):
                with ui.card(full_screen=False):
                    ui.card_header("🔎 Фильтры")
                    ui.input_date_range("pub_date", "Дата публикации вакансии", start="2024-01-01",
                                        end="2024-12-31", min="2024-01-01", max="2024-12-31", width=250)
                    ui.input_selectize("experience", "Опыт работы",
                                       choices=[], multiple=True, width=250)
                    ui.input_selectize("region", "Регион", choices=[],
                                       multiple=True, width=250)
                    ui.input_slider("salary", "Заработная плата",
                                    min=0, max=100000, value=[0, 100000])
                with ui.card(full_screen=True):
                    ui.card_header("🔗 Граф")

                    @render_widget
                    def widget():
                        if filtered_data().empty:
                            ui.notification_show(
                                ui="Ошибка", action="Нет данных, соответствующих выбранным фильтрам", type="error", duration=10)
                            return None
                        G = bipartite_graph()
                        if G is None:
                            ui.notification_show(
                                ui="Ошибка", action="Нет данных для построения графа", type="error", duration=10)
                            return None
                        return Sigma(G, node_size=list(dict(G.degree()).values()),
                                     node_size_range=(1, 10),
                                     node_metrics=['louvain'],
                                     node_color='louvain',
                                     node_border_color_from='node')

        with ui.nav_panel("Одномодальный граф"):
            with ui.layout_columns(col_widths=(3, 9)):
                with ui.card(full_screen=False):
                    ui.card_header("🔎 Фильтры")
                    ui.input_date_range("pub_date_sem", "Дата публикации вакансии", start="2024-01-01",
                                        end="2024-12-31", min="2024-01-01", max="2024-12-31", width=250)
                    ui.input_selectize("experience_sem", "Опыт работы",
                                       choices=[], multiple=True, width=250)
                    ui.input_selectize("region_sem", "Регион", choices=[],
                                       multiple=True, width=250)
                    ui.input_slider("salary_sem", "Заработная плата",
                                    min=0, max=100000, value=[0, 100000])
                    ui.input_selectize("specialty", "Название специальности",
                                       choices=[], multiple=True, width=250)
                with ui.card(full_screen=True):
                    ui.card_header("🔗 Семантический граф")

                    @render_widget
                    def widget_semantic():
                        if filtered_data_semantic().empty:
                            ui.notification_show(
                                ui="Ошибка", action="Нет данных, соответствующих выбранным фильтрам", type="error", duration=10)
                            return None
                        G = semantic_graph()
                        if G is None:
                            ui.notification_show(
                                ui="Ошибка", action="Нет данных для построения графа", type="error", duration=10)
                            return None
                        return Sigma(G, node_size=list(dict(G.degree()).values()),
                                     node_size_range=(1, 10),
                                     node_metrics=['louvain'],
                                     node_color='louvain',
                                     node_border_color_from='node')


with ui.nav_panel("Рекомендация", icon=icon_svg('diagram-project')):
    with ui.navset_card_underline(id="selected_navset_card_underline"):
        with ui.nav_panel("Рекомендация схожих узлов"):
            with ui.layout_columns(col_widths=(6, 6)):
                with ui.card(full_screen=True):
                    ui.card_header("📊 Рекомендация схожих узлов № 1")

                    with ui.layout_columns(col_widths={"sm": (6, 6, 12)}):
                        ui.input_selectize(
                            "node_1", "Выбрать узел:", choices=[])
                        ui.input_selectize(
                            "node_type_1", "Выбрать тип узла:", choices=["Специальность", "Навык"])
                        ui.input_numeric("obs_1", "Количество наблюдений:",
                                         5, min=1, max=30, width="750px")
                    ui.hr()

                    @reactive.effect
                    def update_node_choices_1():
                        matrix = skills_roles_matrix()
                        if matrix.empty:
                            ui.update_selectize("node_1", choices=[])
                        else:
                            choices = list(matrix.columns) + list(matrix.index)
                            ui.update_selectize("node_1", choices=choices)

                    @render_plotly
                    def recommendations_plot_1():
                        if filtered_data().empty:
                            ui.notification_show(
                                ui="Ошибка", action="Нет данных, соответствующих выбранным фильтрам", type="error", duration=10)
                            return None
                        G = bipartite_graph()
                        node = input.node_1()
                        node_type = input.node_type_1()
                        level_target = "first" if node_type == "Специальность" else "second"
                        top_n = input.obs_1()

                        if not node:
                            return px.bar(x=["Нет выделенных узлов"], y=[0], template="plotly_white").update_layout()

                        recs = netfunction.recommend_similar_nodes(
                            G, node, level_target=level_target, top_n=top_n)
                        nodes, similarities = zip(*recs)
                        unique_nodes = list(set(nodes))
                        colors = px.colors.qualitative.G10
                        color_map = {
                            n: colors[i % len(colors)] for i, n in enumerate(unique_nodes)}

                        fig = px.bar(y=nodes, x=similarities,
                                     labels={'x': 'Сходство', 'y': ''},
                                     title=f'Топ {top_n} схожих узлов для узла "{node}"',
                                     color=nodes, template="plotly_white",
                                     color_discrete_map=color_map).update_layout(showlegend=False, title_x=0.5)
                        return fig

                with ui.card(full_screen=True):
                    ui.card_header("📊 Рекомендация схожих узлов № 2")

                    with ui.layout_columns(col_widths={"sm": (6, 6, 12)}):
                        ui.input_selectize(
                            "node_2", "Выбрать узел:", choices=[])
                        ui.input_selectize(
                            "node_type_2", "Выбрать тип узла:", choices=["Специальность", "Навык"])
                        ui.input_numeric("obs_2", "Количество наблюдений:",
                                         5, min=1, max=30, width="750px")
                    ui.hr()

                    @reactive.effect
                    def update_node_choices_2():
                        matrix = skills_roles_matrix()
                        if matrix.empty:
                            ui.update_selectize("node_2", choices=[])
                        else:
                            choices = list(matrix.columns) + list(matrix.index)
                            ui.update_selectize("node_2", choices=choices)

                    @render_plotly
                    def recommendations_plot_2():
                        if filtered_data().empty:
                            ui.notification_show(
                                ui="Ошибка", action="Нет данных, соответствующих выбранным фильтрам", type="error", duration=10)
                            return None
                        G = bipartite_graph()
                        node = input.node_2()
                        node_type = input.node_type_2()
                        level_target = "first" if node_type == "Специальность" else "second"
                        top_n = input.obs_2()

                        if not node:
                            return px.bar(x=["No node selected"], y=[0], template="plotly_white").update_layout()

                        recs = netfunction.recommend_similar_nodes(
                            G, node, level_target=level_target, top_n=top_n)
                        nodes, similarities = zip(*recs)
                        unique_nodes = list(set(nodes))
                        colors = px.colors.qualitative.G10
                        color_map = {
                            n: colors[i % len(colors)] for i, n in enumerate(unique_nodes)}

                        fig = px.bar(y=nodes, x=similarities,
                                     labels={'x': 'Сходство', 'y': ''},
                                     title=f'Топ {top_n} схожих узлов для узла "{node}"',
                                     color=nodes, template="plotly_white",
                                     color_discrete_map=color_map).update_layout(showlegend=False, title_x=0.5)
                        return fig

        with ui.nav_panel("Рекомендация соседних узлов"):
            with ui.layout_columns(col_widths=(6, 6)):
                with ui.card(full_screen=True):
                    ui.card_header("📊 Рекомендация соседних узлов № 1")

                    with ui.layout_columns(col_widths={"sm": (6, 6, 12)}):
                        ui.input_selectize(
                            "node3", "Выбрать узел:", choices=[])
                        ui.input_selectize("node_type3", "Выбрать тип узла:",
                                           choices=["Специальность", "Навык"])
                        ui.input_numeric("obs3", "Количество наблюдений:", 5, min=1,
                                         max=30, width="750px")

                    ui.hr()

                    @reactive.effect
                    def update_node3_choices():
                        matrix = skills_roles_matrix()
                        if matrix.empty:
                            ui.update_selectize("node3", choices=[])
                        else:
                            choices = list(matrix.columns) + list(matrix.index)
                            ui.update_selectize("node3", choices=choices)

                    @render_plotly
                    def neighbor_recommendations_plot_1():
                        if filtered_data().empty:
                            ui.notification_show(ui="Ошибка",
                                                 action="Нет данных, соответствующих выбранным фильтрам",
                                                 type="error",
                                                 duration=10)
                            return None
                        G = bipartite_graph()
                        node = input.node3()
                        node_type = input.node_type3()
                        level_target = "first" if node_type == "Специальность" else "second"
                        top_n = input.obs3()

                        if not node:
                            return px.bar(x=["No node selected"], y=[0], template="plotly_white").update_layout()

                        recs = netfunction.neighbor_recommendations(
                            G, node, level_target=level_target, top_n=top_n)

                        try:
                            nodes, similarities = zip(*recs)
                        except ValueError:
                            return px.bar(x=["No node selected"], y=[0], template="plotly_white").update_layout()

                        unique_nodes = list(set(nodes))
                        colors = px.colors.qualitative.G10
                        color_map = {
                            n: colors[i % len(colors)] for i, n in enumerate(unique_nodes)}
                        fig = px.bar(y=nodes, x=similarities,
                                     labels={'x': 'Вес', 'y': ''},
                                     title=f'Топ {top_n} соседей для узла "{node}"',
                                     color=nodes,
                                     template="plotly_white",
                                     color_discrete_map=color_map).update_layout(showlegend=False, title_x=0.5)
                        return fig
                # Новый
                with ui.card(full_screen=True):
                    ui.card_header("📊 Рекомендация соседних узлов № 2")

                    with ui.layout_columns(col_widths={"sm": (6, 6, 12)}):
                        ui.input_selectize(
                            "node4", "Выбрать узел:", choices=[])
                        ui.input_selectize("node_type4", "Выбрать тип узла:",
                                           choices=["Специальность", "Навык"])
                        ui.input_numeric(
                            "obs4", "Количество наблюдений:", 5, min=1, max=30, width="750px")

                    ui.hr()

                    @reactive.effect
                    def update_node4_choices():
                        matrix = skills_roles_matrix()
                        if matrix.empty:
                            ui.update_selectize("node4", choices=[])
                        else:
                            choices = list(matrix.columns) + list(matrix.index)
                            ui.update_selectize("node4", choices=choices)

                    @render_plotly
                    def neighbor_recommendations_plot_2():
                        if filtered_data().empty:
                            ui.notification_show(ui="Ошибка",
                                                 action="Нет данных, соответствующих выбранным фильтрам",
                                                 type="error",
                                                 duration=10)
                            return None
                        G = bipartite_graph()
                        node = input.node4()
                        node_type = input.node_type4()
                        level_target = "first" if node_type == "Специальность" else "second"
                        top_n = input.obs4()

                        if not node:
                            return px.bar(x=["No node selected"], y=[0], template="plotly_white").update_layout()

                        recs = netfunction.neighbor_recommendations(
                            G, node, level_target=level_target, top_n=top_n)

                        try:
                            nodes, similarities = zip(*recs)
                        except ValueError:
                            return px.bar(x=["No node selected"], y=[0], template="plotly_white").update_layout()

                        unique_nodes = list(set(nodes))
                        colors = px.colors.qualitative.G10
                        color_map = {
                            n: colors[i % len(colors)] for i, n in enumerate(unique_nodes)}
                        fig = px.bar(y=nodes, x=similarities,
                                     labels={'x': 'Вес', 'y': ''},
                                     title=f'Топ {top_n} соседей для узла "{node}"',
                                     color=nodes,
                                     template="plotly_white",
                                     color_discrete_map=color_map).update_layout(showlegend=False, title_x=0.5)
                        return fig


ui.nav_spacer()
with ui.nav_control():
    ui.input_dark_mode(id="mode")
