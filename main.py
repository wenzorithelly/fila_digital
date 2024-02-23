import os
import flet as ft
from pages.presence import ListPresence
from pages.control import Control
from pages.settings import Settings
from pages.dashboard import Dashboard


class LoginPage(ft.SafeArea):
    def __init__(self, app: 'App'):
        super().__init__()
        self.app = app
        self.page = self.app.page
        self.login_input: ft.TextField = ft.TextField(expand=True, hint_text="Enter your password", height=50,
                                                      border_radius=12, content_padding=7,
                                                      keyboard_type=ft.KeyboardType.NUMBER,
                                                      password=True, on_submit=lambda e: self.handle_login(e))
        self.login_button: ft.ElevatedButton = ft.ElevatedButton(
            text="Entrar",
            bgcolor=ft.colors.WHITE,
            color=ft.colors.GREY_800,
            height=55,
            width=120,
            on_click=lambda e: self.handle_login(e)
        )
        self.content: ft.Column = ft.Column(
            controls=[
                ft.Divider(height=80, color=ft.colors.TRANSPARENT),
                ft.Divider(height=80, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[ft.Icon(name=ft.icons.LOCK, size=80)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=30, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.login_input]),
                ft.Divider(height=60, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.login_button], alignment=ft.MainAxisAlignment.CENTER)
            ]
        )

    def handle_login(self, e):
        if self.login_input.value == os.environ.get('APP_PASSWORD'):
            self.app.is_authenticated = True
            self.app.switch_view()


class App(ft.SafeArea):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.is_authenticated = False
        self.page.navigation_bar = ft.CupertinoNavigationBar(
            bgcolor=ft.colors.GREY_900 if page.theme_mode == ft.ThemeMode.DARK else ft.colors.GREY_400,
            selected_index=0,
            active_color=ft.colors.WHITE70,
            height=page.window_height + 80,
            on_change=self.change_tab,
            destinations=[
                ft.NavigationDestination(icon=ft.icons.HOME_OUTLINED, selected_icon=ft.icons.HOME_ROUNDED),
                ft.NavigationDestination(icon=ft.icons.SEND_OUTLINED, selected_icon=ft.icons.SEND_SHARP),
                ft.NavigationDestination(icon=ft.icons.DASHBOARD_OUTLINED, selected_icon=ft.icons.DASHBOARD_ROUNDED),
                ft.NavigationDestination(icon=ft.icons.SETTINGS_OUTLINED, selected_icon=ft.icons.SETTINGS_ROUNDED),
            ]
        )
        self.show_login_page()
        self.control: Control = Control(page, visible=True)
        self.presence: ListPresence = ListPresence(page, visible=False, control=self.control)
        self.dashboard: Dashboard = Dashboard(page, visible=False)
        self.settings: Settings = Settings(page, visible=False)

        self.main: ft.Column = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column([
                        self.control,
                        self.presence,
                        self.dashboard,
                        self.settings
                    ]))
            ], scroll=ft.ScrollMode.ALWAYS
        )

    def change_tab(self, e):
        my_index = e.control.selected_index
        self.control.visible = my_index == 0
        self.presence.visible = my_index == 1
        self.dashboard.visible = my_index == 2
        self.settings.visible = my_index == 3
        self.page.update()

    def show_login_page(self):
        self.content = LoginPage(self)
        self.page.navigation_bar.visible = False

    def switch_view(self):
        if self.is_authenticated:
            self.content = self.main
            self.page.navigation_bar.visible = True
        else:
            self.show_login_page()
        self.page.update()


# ==============================================
# MAIN FUNCTION
# ==============================================
def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK
    theme = ft.Theme()
    page.theme = theme
    print(19)
    app: App = App(page)
    page.add(app)
    page.update()


if __name__ == "__main__":
    ft.app(target=main)
