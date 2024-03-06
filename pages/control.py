import flet as ft
import os
import requests
import time
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
        result = supabase.table("clients").select("first_name, last_name, number, entered_at").is_("message_sent", "TRUE").is_("left_at", "NULL").order("first_name").execute()
        clients = result.data

        name_list = [{'name': f"{client['first_name']} {client['last_name']}", 'phone': client['number'], 'entered_at': client.get('entered_at') is not None} for client in clients if client.get('first_name')]

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


def fetch_default_message(page: ft.Page) -> dict:
    try:
        result = supabase.table("messages").select("id, content").is_("default_message", "true").limit(1).execute()
        message = result.data[0] if result.data else None

        return {'id': message['id'], 'message': message['content']} if message else {}

    except Exception as a:
        display_error_banner(page, a)
        return {}


def send_message(number, message, page: ft.Page):
    def remove_ninth_digit(phone):
        phone_number = phone
        number_str = str(phone_number)
        if len(number_str) > 10 and number_str[2] == '9':
            phone_number = number_str[:2] + number_str[3:]

        return phone_number

    whatsapp = remove_ninth_digit(number)
    headers = {
        "Authorization": "Bearer " + os.environ.get("WAAPI_TOKEN"),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "chatId": f"55{whatsapp}@c.us",
        "message": f"{message}"
    }
    endpoint = 'https://waapi.app/api/v1/instances/6309/client/action/send-message'
    response = requests.post(endpoint, json=payload, headers=headers)
    if response.json()["data"]["status"] == 'success':
        page.snack_bar = ft.SnackBar(
            bgcolor=ft.colors.GREEN_300,
            content=ft.Text(f"Mensagem Enviada!")
        )
        page.snack_bar.open = True
        page.update()
    else:
        page.snack_bar = ft.SnackBar(
            bgcolor=ft.colors.RED_300,
            content=ft.Text(f'Erro ao enviar mensagem: {response.json()["data"]["status"]}')
        )
        page.snack_bar.open = True
        page.update()


toggle_style_sheet: dict = {"icon": ft.icons.REFRESH_ROUNDED, "icon_size": 20}
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
        self.title: ft.Text = ft.Text("Controle de Sala", size=20, weight=ft.FontWeight.W_800)
        self.toggle: ft.IconButton = ft.IconButton(
            **toggle_style_sheet, on_click=lambda e: self.refresh(e)
        )
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
        self.message_data = fetch_default_message(page=self.page)
        self._text_message = self.message_data["message"] if self.message_data else "Olá, sua vez chegou"
        self.send_button: ft.ElevatedButton = ft.ElevatedButton(
            text="Reenviar",
            icon=ft.icons.SEND_ROUNDED,
            bgcolor=ft.colors.GREEN_700,
            color=ft.colors.WHITE,
            height=30,
            on_click=self.send_messages  # Bind the send_messages function
        )
        self.check_selection_state()
        self.search: ft.IconButton = ft.IconButton(**search_style_sheet, on_click=lambda e: self.search_items())
        self.total_counter: ft.Text = ft.Text(f"Total: {len(self.data)}", italic=True)
        self.presence_counter_indicator = self.update_presence_counter()
        self.presence_counter: ft.Text = ft.Text(f"Pessoas na sala: {self.presence_counter_indicator}", italic=True)

        self.main: ft.Column = ft.Column(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[self.title, self.toggle]
                ),
                ft.Divider(height=5),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.item, self.search], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10),
                ft.Container(content=self.list_names, height=self.page.window_height+320, expand=False),
                ft.Divider(height=10),
                ft.Row(controls=[self.presence_counter, self.total_counter], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=12, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.present, self.left],
                       alignment=ft.MainAxisAlignment.CENTER,
                       spacing=40
                       ),
                ft.Row([
                    self.send_button
                ], alignment=ft.MainAxisAlignment.CENTER)
            ], scroll=ft.ScrollMode.ALWAYS
        )
        self.content = self.main
        self.room_list()

    def room_list(self):
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

    def send_messages(self, e):
        self.send_button.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.colors.WHITE)
        self.send_button.icon = None
        self.page.update()
        selected_clients = [client.client for client in self.list_names.controls if isinstance(client, ClientName) and client.selected]

        for client in selected_clients:
            send_message(client['phone'], self._text_message, page=self.page)
            time.sleep(2)

        self.send_button.content = None
        self.send_button.icon = ft.icons.SEND_ROUNDED
        self.send_button.text = "Reenviar"
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

        self.send_button.content = None
        self.send_button.text = "Enviar"

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

    def refresh(self, e):
        self.toggle.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.colors.WHITE)
        self.toggle.icon = None
        self.page.update()

        self.refresh_list()

        self.toggle.icon = ft.icons.REFRESH_ROUNDED
        self.page.update()
