import flet as ft
import os
import time
from supabase import create_client
from dotenv import load_dotenv
import requests

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
        result = supabase.table("clients").select("first_name, last_name, number").is_("message_sent", "FALSE").order("created_at", desc=False).execute()
        clients = result.data

        name_list = [{'name': f"{client['first_name']} {client['last_name']}", 'phone': client['number']} for client in clients if client['first_name']]

        return name_list

    except Exception as a:
        display_error_banner(page, a)
        return []


def fetch_default_message(page: ft.Page) -> dict:
    try:
        result = supabase.table("messages").select("id, content").is_("default_message", "true").limit(1).execute()
        message = result.data[0] if result.data else None

        return {'id': message['id'], 'message': message['content']} if message else {}

    except Exception as a:
        display_error_banner(page, a)
        return {}


def update_message_sent_status(client_phone, page: ft.Page):
    try:
        supabase.table("clients").update({"message_sent": "TRUE"}).eq("number", client_phone).execute()

    except Exception as a:
        display_error_banner(page, a)


def delete_client(client_phone, page: ft.Page):
    try:
        supabase.table("clients").delete().eq("number", client_phone).execute()

    except Exception as a:
        display_error_banner(page, a)


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


# ==============================================
# STYLESHEETS
# ==============================================
toggle_style_sheet: dict = {"icon": ft.icons.REFRESH_ROUNDED, "icon_size": 20}
search_style_sheet: dict = {"icon": ft.icons.SEARCH_ROUNDED, "icon_size": 25}
item_style_sheet: dict = {"height": 35, "expand": True, "cursor_height": 15, "hint_text": "Pesquisar um nome...", "content_padding": 7, "border_radius": 12}
client_name_style_sheet: dict = {"height": 40}


# ==============================================
# NAMES LIST
# ==============================================
class ClientName(ft.Container):
    def __init__(self, hero: "ListPresence", client: dict) -> None:
        super().__init__(**client_name_style_sheet)

        self.hero = hero
        self.client: dict = client
        self.selected: bool = False

        self.tick = ft.Checkbox(on_change=self.toggle_select)
        self.text: ft.Text = ft.Text(self.client['name'], size=15)
        self.delete: ft.IconButton = ft.IconButton(icon=ft.icons.DELETE_ROUNDED, icon_color=ft.colors.RED_700,
                                                   on_click=lambda e: self.on_delete_clicked())
        self.content: ft.Row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(controls=[self.tick, self.text]), self.delete
            ]
        )

    def toggle_select(self, e):
        self.selected = not self.selected
        self.hero.check_selection_state()

    def on_delete_clicked(self):
        self.delete.content = ft.ProgressRing(width=10, height=10, stroke_width=2, color=ft.colors.WHITE)
        self.delete.icon = None
        self.hero.page.update()

        delete_client(self.client['phone'], page=self.hero.page)
        self.hero.refresh_everything()


# ==============================================
# CALL USERS INTERFACE
# ==============================================
class ListPresence(ft.SafeArea):
    def __init__(self, page: ft.Page = None, visible: bool = False, control=None):
        super().__init__(visible=visible)
        self.page = page
        self.control = control
        self.title: ft.Text = ft.Text("Lista de Presença", size=20, weight=ft.FontWeight.W_800)
        self.toggle: ft.IconButton = ft.IconButton(
            **toggle_style_sheet, on_click=lambda e: self.refresh(e)
        )
        self.item: ft.TextField = ft.TextField(**item_style_sheet, on_submit=lambda e: self.search_items())
        self.data = fetch_data(page=self.page)
        self.message_data = fetch_default_message(page=self.page)
        self._text_message = self.message_data["message"] if self.message_data else "Olá, sua vez chegou"
        self.list_names: ft.ListView = ft.ListView(expand=True, spacing=5)
        self.search: ft.IconButton = ft.IconButton(**search_style_sheet, on_click=lambda e: self.search_items())

        self.counter: ft.Text = ft.Text(f"Total: {len(self.data)}", italic=True)
        self.send_button: ft.ElevatedButton = ft.ElevatedButton(
            text="Enviar Mensagem",
            icon=ft.icons.SEND_ROUNDED,
            bgcolor=ft.colors.GREEN_700,
            color=ft.colors.WHITE,
            height=50,
            on_click=self.send_messages  # Bind the send_messages function
        )
        self.check_selection_state()
        self.main: ft.Column = ft.Column(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[self.title, self.toggle]
                ),
                ft.Divider(height=5),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.item, self.search], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                ft.Container(content=self.list_names, height=self.page.window_height+320, expand=False),
                ft.Divider(height=10),
                ft.Row(controls=[self.counter], alignment=ft.MainAxisAlignment.END),
                ft.Divider(height=12, color=ft.colors.TRANSPARENT),
                ft.Row(controls=[self.send_button],
                       alignment=ft.MainAxisAlignment.CENTER)
            ], scroll=ft.ScrollMode.ALWAYS
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
            update_message_sent_status(client['phone'], page=self.page)
            time.sleep(2)

        self.refresh_everything()

    def reset_send_button(self):
        self.send_button.text = "Enviar Mensagem"
        self.send_button.icon = ft.icons.SEND_ROUNDED

    def refresh_everything(self):
        self.data = fetch_data(page=self.page)
        self.list_names.controls.clear()
        self.to_call_list()
        self.item.value = ""
        self.reset_send_button()
        self.control.refresh_list()
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
            self.send_button.disabled = False
            self.page.update()
        else:
            self.send_button.disabled = True
            self.page.update()

    def refresh(self, e):
        self.toggle.content = ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.colors.WHITE)
        self.toggle.icon = None
        self.page.update()

        self.refresh_everything()

        self.toggle.icon = ft.icons.REFRESH_ROUNDED
        self.page.update()
