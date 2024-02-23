import flet as ft
import plotly.express as px
from flet.plotly_chart import PlotlyChart
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import pytz
import base64
import os

load_dotenv()
supabaseUrl = "https://joypeidfaomfvofhtiwb.supabase.co"
supabaseKey = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url=supabaseUrl, supabase_key=supabaseKey)


class Charts:
    def __init__(self):
        clients_data = self.fetch_data()
        self.df = pd.DataFrame(clients_data)
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        self.df['created_at'] = pd.to_datetime(self.df['created_at'], errors='coerce')
        self.df['entered_at'] = pd.to_datetime(self.df['entered_at'], errors='coerce')
        self.df['left_at'] = pd.to_datetime(self.df['left_at'], errors='coerce')
        self.df['created_at'] = self.df['created_at'].dt.tz_convert(brazil_tz)
        self.df['entered_at'] = self.df['entered_at'].dt.tz_convert(brazil_tz)
        self.df['left_at'] = self.df['left_at'].dt.tz_convert(brazil_tz)
        self.df['time_in_room'] = self.df['left_at'] - self.df['entered_at']

    @staticmethod
    def fetch_data():
        clients_data = supabase.table('clients').select('*').execute().data
        return clients_data

    def presences_and_absences(self):

        normal_radius = 50
        hover_radius = 60
        normal_title_style = ft.TextStyle(
            size=16, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD
        )
        hover_title_style = ft.TextStyle(
            size=22,
            color=ft.colors.WHITE,
            weight=ft.FontWeight.BOLD,
            shadow=ft.BoxShadow(blur_radius=2, color=ft.colors.BLACK54),
        )

        presence_grouped_all = self.df.groupby(['presence'], observed=True).size().reset_index(name='count')
        color_mapping = {True: '#636EFA', False: '#EE553B'}

        pie_sections = [
            ft.PieChartSection(
                count,
                title=f"{count}",
                title_style=normal_title_style,
                color=color_mapping[presence],
                radius=normal_radius,
                badge=ft.Text("Presentes") if presence else ft.Text("Ausentes"),
                badge_position=1.2
            ) for presence, count in zip(presence_grouped_all['presence'], presence_grouped_all['count'])
        ]

        chart = ft.PieChart(
            sections=pie_sections,
            sections_space=0,
            center_space_radius=40,
            on_chart_event=None,
        )

        def on_chart_event(e: ft.PieChartEvent):
            for idx, section in enumerate(chart.sections):
                if idx == e.section_index:
                    section.radius = hover_radius
                    section.title_style = hover_title_style
                else:
                    section.radius = normal_radius
                    section.title_style = normal_title_style
            chart.update()

        chart.on_chart_event = on_chart_event

        return chart

    def presence_per_session(self):
        today = datetime.now().date()
        data = self.df.loc[self.df['entered_at'].dt.date == today].copy()
        data.loc[:, 'group'] = pd.cut(
            data['entered_at'].dt.hour, bins=[7, 14, 18, 23],
            labels=['8h - 13h', '14h - 18h', '19h - 22h'])
        prayers_per_session = data[['entered_at', 'group']]
        grouped_prayers_per_session = prayers_per_session.groupby('group',
                                                                  observed=True).size().reset_index(name='count')

        def color_mapping(grp):
            if grp == "8h - 13h":
                return ft.colors.BLUE_600
            elif grp == "14h - 18h":
                return ft.colors.ORANGE_600
            else:
                return ft.colors.YELLOW_600

        bar_groups = [
            ft.BarChartGroup(
                x=i,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=quantity,
                        width=40,
                        color=color_mapping(name),
                        border_radius=0,
                    ),
                ],
            ) for i, (name, quantity) in enumerate(zip(grouped_prayers_per_session['group'],
                                                       grouped_prayers_per_session['count']))
        ]

        chart = ft.BarChart(
            bar_groups=bar_groups,
            border=ft.border.all(1, ft.colors.GREY_400),
            left_axis=ft.ChartAxis(
                labels_size=40, title_size=40, labels_interval=1
            ),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=i, label=ft.Container(ft.Text(name), padding=10))
                    for i, name in enumerate(grouped_prayers_per_session['group'])
                ],
                labels_size=40,
            ),
            max_y=grouped_prayers_per_session['count'].max() + 2,
            expand=True,
        )

        return chart


toggle_style_sheet: dict = {"icon": ft.icons.REFRESH_ROUNDED, "icon_size": 18}


class Dashboard(ft.SafeArea):
    def __init__(self, page: ft.Page, visible: bool = False):
        super().__init__(visible=visible)
        self.page = page
        self.charts = Charts()
        self.title: ft.Text = ft.Text("Dashboard", size=20, weight=ft.FontWeight.W_800)
        self.toggle: ft.IconButton = ft.IconButton(
            **toggle_style_sheet, on_click=lambda e: self.refresh(e)
        )

        self.presences_and_absences = self.charts.presences_and_absences()
        self.presence_per_session = self.charts.presence_per_session()
        self.main: ft.Column = ft.Column([
            ft.Container(content=ft.Column([
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[self.title, self.toggle]
                ),
                ft.Divider(height=5),
                ft.Divider(height=10, color="transparent"),


                ft.Container(content=self.presences_and_absences, alignment=ft.alignment.center),
                ft.Row(controls=[ft.Text("HOJE: Presenças por Sessão", size=18, weight=ft.FontWeight.W_500)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(content=self.presence_per_session, alignment=ft.alignment.center)
            ]), expand=True)
        ],
            scroll=ft.ScrollMode.ALWAYS)

        self.content = self.main

    def refresh(self, e):
        self.toggle.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.colors.WHITE)
        self.toggle.icon = None
        self.page.update()

        self.charts.fetch_data()

        self.toggle.icon = ft.icons.REFRESH_ROUNDED
        self.page.update()
