from config import get_timestamp_seconds, create_config, config_found, get_port
from keys import load_keys, keyfile_found, save_keys, generate_keys
from log_ops import get_logger
from transaction_ops import create_transaction, to_raw_amount, get_recommneded_fee
import random
from dircheck import make_folder
from peer_ops import load_ips
import json
import requests
import asyncio
from data_ops import get_home


def send_transaction(address, recipient, amount, data, public_key, private_key, target, port):
    transaction = create_transaction(sender=address,
                                     recipient=recipient,
                                     amount=to_raw_amount(amount),
                                     data=data,
                                     fee=get_recommneded_fee(target=target,
                                                             port=port)+1,
                                     public_key=public_key,
                                     private_key=private_key,
                                     timestamp=get_timestamp_seconds())

    print(json.dumps(transaction, indent=4))
    input("Press any key to continue")
    result = requests.get(f"http://{target}:{port}/submit_transaction?data={json.dumps(transaction)}", timeout=30)
    result_json = json.loads(result.text)

    if result_json["result"]:
        print("Transaction submitted successfully")
    else:
        print(f"Transaction failed: {result_json['message']}")

if __name__ == "__main__":
    logger = get_logger(file=f"{get_home()}/wallet.log")

    make_folder(f"{get_home()}/private", strict=False)
    if not config_found():
        create_config()
    if not keyfile_found():
        save_keys(generate_keys())
    keydict = load_keys()

    private_key = keydict["private_key"]
    public_key = keydict["public_key"]
    address = keydict["address"]
    target = random.choice(asyncio.run(load_ips()))
    port = get_port()

    print(f"Sending from {address}")
    recipient = input("Recipient: ")
    amount = input("Amount: ")

    send_transaction(address=address,
                     amount=amount,
                     data="",
                     port=port,
                     private_key=private_key,
                     public_key=public_key,
                     recipient=recipient,
                     target=target)

