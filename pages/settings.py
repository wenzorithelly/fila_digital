import flet as ft
import os
from supabase import create_client
from datetime import datetime

supabaseUrl = "https://joypeidfaomfvofhtiwb.supabase.co"
supabaseKey = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url=supabaseUrl, supabase_key=supabaseKey)


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
        result = supabase.table("messages").select("id, content, default_message").order("updated_at", desc=True).execute()
        messages = result.data

        message_list = [{'id': message['id'], 'message': message['content'], 'default': message['default_message']} for message in messages]

        return message_list

    except Exception as a:
        display_error_banner(page, a)
        return []


def insert_message(content, page: ft.Page):
    try:
        result = supabase.table("messages").insert({"content": content}).execute()

        return True if result.status_code in range(200, 300) else False
    except Exception as a:
        display_error_banner(page, a)
        return False


def update_default_message(message_id, page: ft.Page):
    try:
        # Set all messages default_message to FALSE
        supabase.table("messages").update({"default_message": "FALSE"}).is_("default_message", "TRUE").execute()

        # Set the selected message default_message to TRUE
        now = datetime.now()
        result = supabase.table("messages").update({"default_message": "TRUE", "updated_at": str(now)}).eq("id", message_id).execute()

        return True
    except Exception as a:
        display_error_banner(page, a)
        return False


def fetch_default_message(page: ft.Page) -> dict:
    try:
        result = supabase.table("messages").select("id, content").is_("default_message", "TRUE").limit(1).execute()
        message = result.data[0] if result.data else None

        return {'id': message['id'], 'message': message['content']} if message else {}

    except Exception as a:
        display_error_banner(page, a)
        return {}


def delete_message(message_id, page: ft.Page):
    try:
        result = supabase.table("messages").delete().eq("id", message_id).execute()

        return True

    except Exception as a:
        display_error_banner(page, a)


class Message(ft.Container):
    def __init__(self, control: 'Settings', client: dict) -> None:
        super().__init__()

        self.client: dict = client
        self.selected: bool = False
        self.is_present: bool = False
        self.control = control
        self.is_default = self.client['id'] if self.client.get('default') is True else None
        self.icon_default = ft.icons.FAVORITE_ROUNDED if self.is_default else ft.icons.FAVORITE_OUTLINE_ROUNDED

        self.text: ft.Text = ft.Text(self.client['message'], size=12)
        self.delete: ft.IconButton = ft.IconButton(icon=ft.icons.DELETE_ROUNDED, icon_color=ft.colors.RED_700,
                                                   on_click=lambda e: self.on_delete_clicked())
        self.favorite: ft.IconButton = ft.IconButton(icon=self.icon_default, on_click=self.save_default_message)
        self.card: ft.Card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        title=ft.Text(self.client['message'])
                    ),
                    ft.Row([
                        self.favorite,
                        self.delete
                    ], alignment=ft.MainAxisAlignment.END)
                ]), width=self.control.page.width-40, padding=5, margin=5
            )
        )
        self.content: ft.Row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(controls=[self.card])
            ]
        )

    def save_default_message(self, e):
        self.favorite.content = ft.ProgressRing(width=10, height=10, stroke_width=2, color=ft.colors.WHITE)
        self.favorite.icon = None
        self.control.page.update()

        update_default_message(self.client['id'], page=self.page)
        self.control.refresh_message_list()
        self.control.page.update()

    def on_delete_clicked(self):
        self.delete.content = ft.ProgressRing(width=10, height=10, stroke_width=2, color=ft.colors.WHITE)
        self.delete.icon = None
        self.control.page.update()

        delete_message(self.client['id'], page=self.control.page)
        self.control.refresh_message_list()


class Settings(ft.SafeArea):
    def __init__(self, page: ft.Page, visible: bool = False):
        super().__init__(visible=visible)
        self.page = page
        self.default_message_id = None
        self.selected_message = None
        self.data = fetch_data(page=self.page)
        self.list_messages: ft.ListView = ft.ListView(expand=True, spacing=2)
        self.add_message: ft.ElevatedButton = ft.ElevatedButton(
            text="Adicionar",
            icon=ft.icons.ADD_ROUNDED,
            bgcolor=ft.colors.BLUE,
            color=ft.colors.WHITE,
            height=50,
            on_click=self.open_dlg
        )
        self.input_message: ft.TextField = ft.TextField(label="Mensagem", expand=True, border_radius=12, multiline=True)
        self.dlg_content: ft.Container = ft.Container(content=ft.Column([
            self.input_message
        ]))
        self.add_dlg: ft.AlertDialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Adicionar Mensagem"),
            content=self.dlg_content,
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_dlg),
                ft.TextButton("Salvar", on_click=self.save_message),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.main: ft.Column = ft.Column(
            controls=[
                ft.Row(controls=[ft.Text("Configurações", size=18, weight=ft.FontWeight.W_600)],
                       alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10, color="transparent"),
                ft.Container(content=self.list_messages, expand=False),
                ft.Divider(height=10),
                ft.Divider(height=12, color="transparent"),
                ft.Row(controls=[self.add_message],
                       alignment=ft.MainAxisAlignment.CENTER)
            ]
        )

        self.content = self.main
        self.message_list()
        self.page.update()

    def message_list(self):
        for client in self.data:
            self.list_messages.controls.append(Message(self, client))
            self.list_messages.controls.append(ft.Divider(height=2, color=ft.colors.TRANSPARENT))
        self.page.update()

    def close_dlg(self, e):
        self.add_dlg.open = False
        self.page.update()

    def open_dlg(self, e):
        self.page.dialog = self.add_dlg
        self.add_dlg.open = True
        self.page.update()

    def save_message(self, e):
        message_content = self.input_message.value
        if message_content.strip() != "":
            success = insert_message(message_content, page=self.page)
            if success:
                self.close_dlg(e)
                self.refresh_message_list()

    def refresh_message_list(self):
        self.data = fetch_data(page=self.page)
        self.list_messages.controls.clear()
        self.message_list()
        self.page.update()
