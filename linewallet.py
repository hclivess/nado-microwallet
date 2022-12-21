from config import get_timestamp_seconds, create_config, config_found, get_port
from keys import load_keys, keyfile_found, save_keys, generate_keys
from log_ops import get_logger
from transaction_ops import create_transaction, to_raw_amount, get_recommneded_fee, to_readable_amount
import random
from dircheck import make_folder
from peer_ops import load_ips
import json
from account_ops import get_account_value
import asyncio
from data_ops import get_home
from compounder import compound_send_transaction
from block_ops import get_penalty

def send_transaction(address, recipient, amount, data, public_key, private_key, ips, fee):
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
    results = asyncio.run(compound_send_transaction(ips=ips,
                                                    port=9173,
                                                    fail_storage=[],
                                                    logger=logger,
                                                    transaction=transaction))

    print(f"Submitted to {len(results)} nodes successfully")


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
    ips = asyncio.run(load_ips(fail_storage=[], logger=logger, port=9173))
    target = random.choice(ips)
    port = get_port()
    balance = get_account_value(address, key="account_balance")
    balance_readable = to_readable_amount(balance)


    print(f"Sending from {address}")
    print(f"Balance: {balance_readable}")
    #print(f"Mining Penalty: {penalty}")
    recipient = input("Recipient: ")
    amount = input("Amount: ")
    fee = input(f"Fee: (Recommended: {get_recommneded_fee(target=target, port=port)})")

    send_transaction(address=address,
                     amount=amount,
                     data="",
                     private_key=private_key,
                     public_key=public_key,
                     recipient=recipient,
                     ips=ips,
                     fee=fee)

