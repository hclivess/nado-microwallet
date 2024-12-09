import json
import os.path
import asyncio
import random
import threading
import time
from ops.transaction_ops import get_target_block
import customtkinter
import requests

from config import get_timestamp_seconds, get_port, create_config, config_found
from ops.key_ops import load_keys, keyfile_found, save_keys, generate_keys
from ops.log_ops import get_logger
from ops.peer_ops import load_ips
from ops.transaction_ops import create_transaction, to_readable_amount, to_raw_amount, get_recommneded_fee, draft_transaction, get_base_fee
from dircheck import make_folder
from ops.data_ops import get_home
from compounder import compound_send_transaction

LOCAL = False
def address_copy():
    app.clipboard_clear()
    app.clipboard_append(address)


def insert_clipboard(where):
    where.delete(0, customtkinter.END)
    where.insert(customtkinter.INSERT, app.clipboard_get())


class Wallet:
    def __init__(self):
        self.target = None
        self.port = get_port()
        self.connected = False
        self.refresh_counter = 10
        self.draft = None
        self.draft_lock = threading.Lock()

    async def init_connect(self):
        failed = []
        if LOCAL:
            self.servers = ["127.0.0.1"]
        else:
            self.servers = await load_ips(fail_storage=failed,
                                          logger=logger,
                                          port=9173,
                                          minimum=1)
        self.target = random.choice(self.servers)
        logger.info(f"Picked {self.target}")
        self.connected = True

    async def reconnect(self):
        failed = []
        if LOCAL:
            servers = ["127.0.0.1"]
        else:
            servers = await load_ips(fail_storage=failed,
                                     logger=logger,
                                     port=9173,
                                     minimum=1)
        if servers:
            self.target = random.choice(servers)
            logger.info(f"Picked {self.target}")
            self.connected = True
        else:
            connection_label.configure(text="Failed to connect")

        self.port = get_port()

    def get_balance(self):
        try:
            url = f"http://{self.target}:{self.port}/get_account?address={address}"
            balance_raw = requests.get(url, timeout=1)
            if balance_raw.status_code != 200:
                balance = 0
            else:
                balance = to_readable_amount(json.loads(balance_raw.text)["balance"])

            balance_var.set(balance)
            connection_label.configure(text=f"Connected to {self.target}")

            self.refresh_counter -= 1
            if self.refresh_counter < 1:
                status_label.configure(text="")

        except Exception as e:
            print(f"Could not connect to get balance from {self.target}: {e}")
            connection_label.configure(text="Disconnected")
            self.connected = False

    async def update_draft(self):
        """Update the transaction draft with current field values"""
        if not self.target:
            return

        try:
            target_block = await get_target_block(target=self.target,
                                                  port=self.port,
                                                  logger=logger)

            with self.draft_lock:
                self.draft = draft_transaction(
                    sender=address,
                    recipient=recipient.get(),
                    amount=to_raw_amount(amount.get()),
                    data={"data": data.get(), "command": command.get()},
                    public_key=public_key,
                    timestamp=get_timestamp_seconds(),
                    target_block=target_block
                )

            fee_raw = await get_recommneded_fee(
                target=self.target,
                port=self.port,
                base_fee=get_base_fee(transaction=self.draft),
                logger=logger
            )
            fee_readable = to_readable_amount(fee_raw)
            init_fee.set(fee_readable)

        except Exception as e:
            print(f"Error updating draft: {e}")
            logger.error(f"Draft update failed: {e}")

    def send_transaction(self):
        # Ensure we have the latest draft before sending
        asyncio.run(self.update_draft())

        with self.draft_lock:
            transaction = create_transaction(
                draft=self.draft,
                fee=to_raw_amount(fee.get()),
                private_key=private_key
            )

        try:
            results = asyncio.run(compound_send_transaction(
                ips=self.servers,
                fail_storage=[],
                logger=logger,
                transaction=transaction,
                port=9173,
                semaphore=asyncio.Semaphore(50)
            ))

            status_label.configure(text=f"{len(results)} nodes accepted")
            self.refresh_counter = 10

        except Exception as e:
            print(f"Could not connect to submit transaction: {e}")
            connection_label.configure(text="Disconnected")
            self.connected = False
            raise


def on_field_change(*args):
    """Callback for when any field changes"""
    if wallet.target:
        app.after(100, lambda: asyncio.run(wallet.update_draft()))


class RefreshClient(threading.Thread):
    def __init__(self, wallet):
        threading.Thread.__init__(self)
        self.quit = False
        self.wallet = wallet

    def run(self):
        while not self.quit:
            if wallet.target:
                wallet.get_balance()
                asyncio.run(wallet.update_draft())
                time.sleep(5)
            elif not wallet.connected and wallet.target:
                asyncio.run(wallet.reconnect())
            else:
                time.sleep(1)


def exit_app():
    refresh.quit = True
    app.quit()

if __name__ == "__main__":
    logger = get_logger(file=f"wallet.log")

    make_folder(f"{get_home()}/private", strict=False)
    if not config_found():
        create_config()
    if not keyfile_found():
        save_keys(generate_keys())

    info_path = os.path.normpath(f'{get_home()}/private/keys.dat')
    logger.info(f"Key location: {info_path}")

    key_dict = load_keys()
    address = key_dict["address"]
    private_key = key_dict["private_key"]
    public_key = key_dict["public_key"]

    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("green")

    app = customtkinter.CTk()
    app.geometry("600x350")
    app.title("NADO MicroWallet")
    app.resizable(0, 0)

    status_label = customtkinter.CTkLabel(master=app, text="", anchor="w")
    status_label.grid(row=7, column=1, columnspan=10, padx=2, pady=2, sticky="w")
    connection_label = customtkinter.CTkLabel(master=app, text="", anchor="w")
    connection_label.grid(row=8, column=1, columnspan=10, padx=2, pady=2, sticky="w")

    sender_button = customtkinter.CTkButton(master=app, text="Sender:", command=lambda: address_copy(), width=50)
    sender_button.grid(row=0, column=0, padx=2, pady=2, sticky="e")

    address_label = customtkinter.CTkLabel(master=app, text=address)
    address_label.grid(row=0, column=1, sticky="w")

    balance_var = customtkinter.StringVar()

    balance_label = customtkinter.CTkLabel(master=app, text="Balance:", anchor="e")
    balance_label.grid(row=1, column=0)
    balance = customtkinter.CTkLabel(master=app, textvariable=balance_var)
    balance.grid(row=1, column=1, sticky="w")

    recipient_button = customtkinter.CTkButton(master=app, text="Recipient:",
                                               command=lambda: insert_clipboard(recipient), width=50)
    recipient_button.grid(row=2, column=0, padx=2, pady=2, sticky="e")

    recipient = customtkinter.CTkEntry(master=app, width=300)
    recipient.grid(row=2, column=1, padx=2, pady=2, sticky="w")

    init_amount = customtkinter.StringVar()
    init_amount.set("0")
    amount_label = customtkinter.CTkLabel(master=app, text="Amount:", anchor="e")
    amount_label.grid(row=3, column=0, padx=2, pady=2)
    amount = customtkinter.CTkEntry(master=app, textvariable=init_amount)
    amount.grid(row=3, column=1, padx=2, pady=2, sticky="w")

    init_fee = customtkinter.StringVar()
    init_fee.set("0")
    fee_label = customtkinter.CTkLabel(master=app, text="Fee:", anchor="e")
    fee_label.grid(row=4, column=0, padx=2, pady=2)
    fee = customtkinter.CTkEntry(master=app, textvariable=(init_fee))
    fee.grid(row=4, column=1, padx=2, pady=2, sticky="w")

    command_label = customtkinter.CTkLabel(master=app, text="Command:", anchor="e")
    command_label.grid(row=5, column=0, padx=2, pady=2)
    command = customtkinter.CTkEntry(master=app)
    command.grid(row=5, column=1, padx=2, pady=2, sticky="w")

    data_label = customtkinter.CTkLabel(master=app, text="Data:", anchor="e")
    data_label.grid(row=6, column=0, padx=2, pady=2)
    data = customtkinter.CTkEntry(master=app, width=300)
    data.grid(row=6, column=1, padx=2, pady=2, sticky="w")

    send_button = customtkinter.CTkButton(master=app, text="Send", command=lambda: wallet.send_transaction())
    send_button.grid(row=9, column=1, padx=2, pady=2, sticky="w")

    quit_button = customtkinter.CTkButton(master=app, text="Quit", command=lambda: exit_app())
    quit_button.grid(row=10, column=1, padx=2, pady=2, sticky="w")

    wallet = Wallet()
    refresh = RefreshClient(wallet=wallet)
    refresh.start()

    connection_label.configure(text="Attempting to connect")
    app.after(250, lambda: asyncio.run(wallet.init_connect()))
    app.mainloop()
