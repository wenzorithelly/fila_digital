import flet as ft
import os
from supabase import create_client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

supabaseUrl = "https://joypeidfaomfvofhtiwb.supabase.co"
supabaseKey = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url=supabaseUrl, supabase_key=supabaseKey)


# ==============================================
# APIs FUNCTIONS
# ==============================================
def display_error_banner(page, error):
    def close_banner(e):
        page.banner.open = False
        page.update()

    page.banner = ft.Banner(
        bgcolor=ft.colors.RED_500,
        leading=ft.Icon(name=ft.icons.WARNING_AMBER_ROUNDED),
        content=ft.Text(f"Error occurred: {error}"),
        actions=[ft.TextButton("Cancel", on_click=close_banner)]
    )
    page.banner.open = True
    page.update()


def fetch_data(page: ft.Page) -> list:
    try:
        result = supabase.table("clients").select("first_name, last_name, number, entered_at").is_("message_sent", "TRUE").is_("left_at", "NULL").execute()
        clients = result.data

        name_list = [{'name': f"{client['first_name']} {client['last_name']}", 'phone': client['number'], 'entered_at': client.get('entered_at') is not None} for client in clients if client.get('first_name') and client.get('last_name')]

        return name_list

    except Exception as a:
        display_error_banner(page, a)
        return []


def update_client_presence(client_phone, page: ft.Page):
    try:
        now = datetime.now()

        data, count = supabase.table("clients").update({"entered_at": str(now), "presence": "TRUE"}).eq("number", client_phone).execute()
        if data:
            return True

    except Exception as a:
        display_error_banner(page, a)
        return False


def update_client_left(client_phone, page: ft.Page):
    try:
        now = datetime.now()

        data, count = supabase.table("clients").update({"left_at": str(now)}).eq("number", client_phone).execute()
        if data:
            return True
    except Exception as a:
        display_error_banner(page, a)
        return False


def delete_client(client_phone, page: ft.Page):
    try:
        supabase.table("clients").delete().eq("number", client_phone).execute()

    except Exception as a:
        display_error_banner(page, a)


toggle_style_sheet: dict = {"icon": ft.icons.DARK_MODE_ROUNDED, "icon_size": 18}
search_style_sheet: dict = {"icon": ft.icons.SEARCH_ROUNDED, "icon_size": 25}
item_style_sheet: dict = {"height": 35, "expand": True, "cursor_height": 15, "hint_text": "Pesquisar um nome...", "content_padding": 7, "border_radius": 12}
client_name_style_sheet: dict = {"height": 40}


class ClientName(ft.Container):
    def __init__(self, control: 'Control', client: dict) -> None:
        super().__init__(**client_name_style_sheet)

        self.client: dict = client
        self.selected: bool = False
        self.is_present: bool = client['entered_at']
        self.control = control

        self.tick = ft.Checkbox(on_change=self.toggle_select)
        self.text: ft.Text = ft.Text(self.client['name'], size=15)
        self.delete: ft.IconButton = ft.IconButton(icon=ft.icons.DELETE_ROUNDED, icon_color=ft.colors.RED_700,
                                                   on_click=lambda e: self.on_delete_clicked())
        self.presence_indicator: ft.Icon = ft.Icon(color=ft.colors.GREEN_600, name=ft.icons.ONLINE_PREDICTION_ROUNDED)
        self.presence_indicator.color = ft.colors.GREEN_600 if self.is_present else ft.colors.TRANSPARENT

        self.content: ft.Row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(controls=[self.tick, self.text, self.presence_indicator]), self.delete
            ]
        )

    def toggle_select(self, e):
        self.selected = not self.selected
        self.control.check_selection_state()

    def mark_as_present(self):
        self.is_present = True
        self.presence_indicator.color = ft.colors.GREEN_600
        self.control.refresh_list()

    def on_delete_clicked(self):
        self.delete.content = ft.ProgressRing(width=10, height=10, stroke_width=2, color=ft.colors.WHITE)
        self.delete.icon = None
        self.control.page.update()

        delete_client(self.client['phone'], page=self.control.page)
        self.control.refresh_list()


class Control(ft.SafeArea):
    def __init__(self, page: ft.Page, visible):
        super().__init__(visible)
        self.page = page
        self.item: ft.TextField = ft.TextField(**item_style_sheet, on_submit=lambda e: self.search_items())
        self.data = fetch_data(page=self.page)
        self.list_names: ft.ListView = ft.ListView(expand=True, spacing=5)
        self.present: ft.ElevatedButton = ft.ElevatedButton(
            text="Entrou",
            icon=ft.icons.CO_PRESENT_ROUNDED,
            bgcolor=ft.colors.BLUE_700,
            color=ft.colors.WHITE,
            height=50,
            width=120,
            on_click=self.change_state
        )
        self.left: ft.ElevatedButton = ft.ElevatedButton(
            text="Saiu",
            icon=ft.icons.DIRECTIONS_WALK_ROUNDED,
            bgcolor=ft.colors.YELLOW_700,
            color=ft.colors.WHITE,
            height=50,
            width=120,
            on_click=self.change_state
        )
        self.check_selection_state()
        self.search: ft.IconButton = ft.IconButton(**search_style_sheet, on_click=lambda e: self.search_items())
        self.total_counter: ft.Text = ft.Text(f"Total: {len(self.data)}", italic=True)
        self.presence_counter_indicator = self.update_presence_counter()
        self.presence_counter: ft.Text = ft.Text(f"Pessoas na sala: {self.presence_counter_indicator}", italic=True)

        self.main: ft.Column = ft.Column(
            controls=[
                ft.Row(controls=[ft.Text("Controle da Sala", size=18, weight=ft.FontWeight.W_600)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[self.item, self.search], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                ft.Container(content=self.list_names, height=self.page.window_height+320, expand=False),
                ft.Divider(height=10),
                ft.Row(controls=[self.presence_counter, self.total_counter], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=12, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.present, self.left],
                       alignment=ft.MainAxisAlignment.CENTER,
                       spacing=40
                       )
            ]
        )
        self.content = self.main
        self.to_call_list()

    def to_call_list(self):
        for client in self.data:
            if self.page.theme_mode == ft.ThemeMode.DARK:
                self.list_names.controls.append(ClientName(self, client))
                self.list_names.controls.append(ft.Divider(height=2))
            else:
                self.list_names.controls.append(ClientName(self, client))
                self.list_names.controls.append(ft.Divider(height=2))

        self.page.update()
        self.presence_counter_indicator = self.update_presence_counter()

    def search_items(self):
        query = self.item.value.lower()

        filtered_data = [name for name in self.data if query in name["name"].lower()]
        self.list_names.controls.clear()

        for client in filtered_data:
            if self.page.theme_mode == ft.ThemeMode.DARK:
                self.list_names.controls.append(ClientName(self, client))
                self.list_names.controls.append(ft.Divider(height=2))
            else:
                self.list_names.controls.append(ClientName(self, client))
                self.list_names.controls.append(ft.Divider(height=2))

        self.page.update()

    def change_state(self, e):
        selected_clients = [client for client in self.list_names.controls if
                            isinstance(client, ClientName) and client.selected]
        if not selected_clients:
            return

        if e.control == self.present:
            self.present.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.colors.WHITE)
            self.present.icon = None
        elif e.control == self.left:
            self.left.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.colors.WHITE)
            self.left.icon = None

        self.page.update()

        for client_name_widget in selected_clients:
            if e.control == self.present:
                success = update_client_presence(client_name_widget.client["phone"], page=self.page)
                if success:
                    client_name_widget.mark_as_present()
            elif e.control == self.left:
                success = update_client_left(client_name_widget.client['phone'], page=self.page)
                if success:
                    self.list_names.controls.remove(client_name_widget)

        self.presence_counter_indicator = self.update_presence_counter()
        self.refresh_list()

    def refresh_list(self):
        self.list_names.controls.clear()
        self.data = fetch_data(page=self.page)
        for client in self.data:
            self.list_names.controls.append(ClientName(self, client))
            self.list_names.controls.append(ft.Divider(height=2))

        self.present.content = None
        self.present.text = "Entrou"
        self.present.icon = ft.icons.CO_PRESENT_ROUNDED

        self.left.content = None
        self.left.text = "Saiu"
        self.left.icon = ft.icons.DIRECTIONS_WALK_ROUNDED

        self.presence_counter_indicator = self.update_presence_counter()
        self.page.update()

    def check_selection_state(self):
        selected_clients = [client for client in self.list_names.controls if
                            isinstance(client, ClientName) and client.selected]
        if selected_clients:
            self.handle_buttons(True)
        else:
            self.handle_buttons(False)

    def handle_buttons(self, is_selected: bool = False):
        if is_selected:
            self.present.disabled = False
            self.left.disabled = False
            self.page.update()
        else:
            self.present.disabled = True
            self.left.disabled = True
            self.page.update()

    def update_presence_counter(self) -> int:
        counter = len([client for client in self.data if client['entered_at']])
        self.page.update()
        return counter
