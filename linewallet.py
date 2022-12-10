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
import msgpack


def send_transaction(address, recipient, amount, data, public_key, private_key, target, port, fee):
    transaction = create_transaction(sender=address,
                                     recipient=recipient,
                                     amount=to_raw_amount(amount),
                                     data=data,
                                     fee=int(fee),
                                     public_key=public_key,
                                     private_key=private_key,
                                     timestamp=get_timestamp_seconds())

    print(json.dumps(transaction, indent=4))
    input("Press any key to continue")
    url = f"http://{target}:{port}/submit_transaction?data={json.dumps(transaction)}"
    result = requests.get(url, timeout=1).content
    result_decoded = msgpack.unpackb(result)["message"]

    print(result_decoded)


if __name__ == "__main__":
    logger = get_logger(file=f"linewallet.log")

    make_folder(f"{get_home()}/private", strict=False)
    if not config_found():
        create_config()
    if not keyfile_found():
        save_keys(generate_keys())
    keydict = load_keys()

    private_key = keydict["private_key"]
    public_key = keydict["public_key"]
    address = keydict["address"]
    target = random.choice(asyncio.run(load_ips(fail_storage=[], logger=logger)))
    port = get_port()

    print(f"Sending from {address}")
    recipient = input("Recipient: ")
    amount = input("Amount: ")
    fee = input(f"Fee: (Recommended: {get_recommneded_fee(target=target, port=port)})")

    send_transaction(address=address,
                     amount=amount,
                     data="",
                     port=port,
                     private_key=private_key,
                     public_key=public_key,
                     recipient=recipient,
                     target=target,
                     fee=fee)

