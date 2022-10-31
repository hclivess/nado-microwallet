import json
import os

import requests

from config import get_timestamp_seconds, get_config
from data_ops import set_and_sort, average
from hashing import blake2b_hash_link
from keys import load_keys
from log_ops import get_logger
from peer_ops import load_peer
from account_ops import get_account_value


def check_block_structure():
    """check timestamp, etc if syncing blocks from others"""
    pass


def get_hash_penalty(a: str, b: str):
    assert a and b, "One of the values to hash is empty"

    shorter_string = min([a, b], key=len)

    score = 0
    for letters in enumerate(shorter_string):
        if b[letters[0]] == (letters[1]):
            score += 1
        score = score + a.count(letters[1])
        score = score + b.count(letters[1])
    return score


def get_block_reward(logger, blocks_backward=100, reward_cap=5000000000):
    """based on number of transactions"""
    latest_block_info = get_latest_block_info(logger=logger)
    parent = latest_block_info["block_hash"]
    latest_block_number = latest_block_info["block_number"]
    block_number = latest_block_number
    tx_count = 0
    reward = 0

    while 0 < block_number > (latest_block_number - blocks_backward):
        block = load_block(parent, logger=logger)
        parent = block["parent_hash"]
        block_number = block["block_number"]

        tx_count += len(block["block_transactions"])

    reward = tx_count * 1000000
    if reward > reward_cap:
        reward = reward_cap

    return reward


def valid_block_gap(logger, new_block, gap=60):
    old_timestamp = get_latest_block_info(logger=logger)["block_timestamp"]
    new_timestamp = new_block["block_timestamp"]

    if get_timestamp_seconds() >= new_timestamp >= old_timestamp + 60:
        return True
    else:
        return False


def get_block_candidate(
        block_producers, block_producers_hash, transaction_pool, logger, peer_file_lock
):
    latest_block = get_latest_block_info(logger=logger)
    best_producer = pick_best_producer(block_producers,
                                       logger=logger,
                                       peer_file_lock=peer_file_lock)

    logger.info(
        f"Producing block candidate for: {block_producers} won by {best_producer}"
    )

    block = construct_block(
        block_number=latest_block["block_number"] + 1,
        parent_hash=latest_block["block_hash"],
        block_ip=best_producer,
        creator=load_peer(logger=logger,
                          ip=best_producer,
                          key="peer_address",
                          peer_file_lock=peer_file_lock),
        transaction_pool=transaction_pool.copy(),
        block_producers_hash=block_producers_hash,
        block_reward=get_block_reward(logger=logger),
        logger=logger,
    )
    return block


def fee_over_blocks(logger, number_of_blocks=250):
    """returns average fee over last x blocks"""
    last_block = get_latest_block_info(logger=logger)

    if last_block["block_number"] < number_of_blocks:
        number_of_blocks = last_block["block_number"]

    fees = []
    for number in range(0, number_of_blocks):
        for transaction in last_block["block_transactions"]:
            fees.append(transaction["fee"])
    if fees:
        return average(fees)
    else:
        return 0
def get_transaction_pool_demo():
    """use for demo only"""
    config = get_config()
    ip = config["ip"]
    port = config["port"]
    tx_pool_message = requests.get(f"http://{ip}:{port}/transaction_pool", timeout=3).text
    tx_pool_dict = json.loads(tx_pool_message)["transaction_pool"]
    return tx_pool_dict


def get_block(block):
    """return transaction based on txid"""
    block_path = f"blocks/{block}.block"
    if os.path.exists(block_path):
        with open(block_path, "r") as file:
            block = json.load(file)
        return block
    else:
        return None


def get_block_producers_hash_demo():
    """use for demo only"""
    config = get_config()
    ip = config["ip"]
    port = config["port"]
    status_message = requests.get(f"http://{ip}:{port}/status", timeout=3).text
    block_producers_hash = json.loads(status_message)["block_producers_hash"]
    return block_producers_hash


def load_block(block_hash: str, logger):
    try:
        with open(f"blocks/{block_hash}.block", "r") as infile:
            return json.load(infile)
    except Exception as e:
        logger.info(f"Failed to load block {block_hash}: {e}")


def load_block_producers() -> list:
    block_producers_path = "index/block_producers.dat"
    if os.path.exists(block_producers_path):
        with open(block_producers_path, "r") as infile:
            return json.load(infile)
    else:
        return []


def save_block_producers(block_producers: list):
    block_producers_path = "index/block_producers.dat"
    with open(block_producers_path, "w") as outfile:
        json.dump(set_and_sort(block_producers), outfile)
    return True


def save_block(block_message: dict, logger):
    try:
        block_hash = block_message["block_hash"]
        with open(f"blocks/{block_hash}.block", "w") as outfile:
            json.dump(block_message, outfile)
        return True
    except Exception as e:
        logger.warning(f"Failed to save block {block_message['block_hash']} due to {e}")


def latest_block_divisible_by(divisor, logger):
    if get_latest_block_info(logger=logger)["block_number"] % divisor == 0:
        return True
    else:
        return False


def get_latest_block_info(logger):
    try:
        with open("index/latest_block.dat", "r") as infile:
            info = load_block(block_hash=json.load(infile), logger=logger)
            return info
    except Exception as e:
        logger.info("Failed to get latest block info")


def set_latest_block_info(block_message: dict):
    try:
        with open("index/latest_block.dat", "w") as outfile:
            json.dump(block_message["block_hash"], outfile)

        with open(
                f"blocks/block_numbers/{block_message['block_number']}.dat", "w"
        ) as outfile:
            json.dump(block_message["block_hash"], outfile)
        with open(f"blocks/block_numbers/index.dat", "w") as outfile:
            json.dump({"last_number": block_message["block_number"]}, outfile)
        return True

    except Exception as e:
        logger.info(f"Failed to set latest block info to {block_message['block_hash']}")
        return False


def construct_block(
        logger,
        block_number: int,
        parent_hash: str,
        creator: str,
        block_ip: str,
        block_producers_hash: str,
        transaction_pool: list,
        block_reward: int,
):
    """timestamp is approximate so hash matches across the network"""

    block_message = {
        "block_number": block_number,
        "block_hash": None,
        "parent_hash": parent_hash,
        "block_ip": block_ip,
        "block_creator": creator,
        "block_timestamp": None,
        "block_transactions": transaction_pool,
        "block_penalty": None,
        "block_producers_hash": block_producers_hash,
        "child_hash": None,
        "block_reward": block_reward,
    }
    block_hash = blake2b_hash_link(link_from=parent_hash, link_to=block_message)
    block_message.update(block_hash=block_hash)
    block_message.update(block_timestamp=get_timestamp_seconds())

    block_penalty = get_penalty(producer_address=creator,
                                block_hash=block_hash)

    block_message.update(block_penalty=block_penalty)
    return block_message


def knows_block(target_peer, hash, logger):
    try:
        url = f"http://{target_peer}:{get_config()['port']}/get_block?hash={hash}"
        if requests.get(url, timeout=3).status_code == 200:
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Failed to check block {hash} from {target_peer}: {e}")
        return False


def update_child_in_latest_block(child_hash, logger):
    """the only method to save block except for creation to avoid read/write collision"""
    parent = get_latest_block_info(logger=logger)
    parent["child_hash"] = child_hash
    save_block(parent, logger=logger)
    return True


def get_blocks_after(target_peer, from_hash, logger, count=50):
    try:
        url = f"http://{target_peer}:{get_config()['port']}/get_blocks_after?hash={from_hash}&count={count}"
        result = requests.get(url, timeout=3)
        text = result.text
        code = result.status_code
        if code == 200:
            return json.loads(text)["blocks_after"]
        else:
            return False

    except Exception as e:
        logger.error(f"Failed to get blocks after {from_hash} from {target_peer}: {e}")
        return False


def get_blocks_before(target_peer, from_hash, logger, count=50):
    try:
        url = f"http://{target_peer}:{get_config()['port']}/get_blocks_before?hash={from_hash}&count={count}"
        result = requests.get(url, timeout=3)
        text = result.text
        code = result.status_code
        if code == 200:
            return json.loads(text)["blocks_before"]
        else:
            return False

    except Exception as e:
        logger.error(f"Failed to get blocks before {from_hash} from {target_peer}: {e}")
        return False


def get_from_single_target(key, target_peer, logger):
    """obtain from a single target"""
    retries = 10

    while retries > 0:
        try:
            url = f"http://{target_peer}:{get_config()['port']}/{key}"
            result = requests.get(url, timeout=3)
            text = result.text
            code = result.status_code

            if code == 200:
                return json.loads(text)[key]
            else:
                return False

        except Exception as e:
            retries -= 1

    if retries < 1:
        logger.error(f"Failed to get block producers from {target_peer}")
        return False


def get_since_last_block(logger) -> [str, None]:
    since_last_block = (
            get_timestamp_seconds()
            - get_latest_block_info(logger=logger)["block_timestamp"]
    )
    return since_last_block


def get_penalty(producer_address, block_hash):
    miner_penalty = get_account_value(address=producer_address, key="account_produced")
    combined_penalty = get_hash_penalty(a=producer_address, b=block_hash) + miner_penalty
    block_penalty = combined_penalty - get_account_value(producer_address, key="account_burned") * 100
    return block_penalty


def pick_best_producer(block_producers, logger, peer_file_lock):
    block_hash = get_latest_block_info(logger=logger)["block_hash"]

    previous_block_penalty = None
    best_producer = None

    for producer_ip in block_producers:
        producer_address = load_peer(logger=logger,
                                     ip=producer_ip,
                                     key="peer_address",
                                     peer_file_lock=peer_file_lock)

        block_penalty = get_penalty(producer_address=producer_address,
                                    block_hash=block_hash)

        if not previous_block_penalty:
            previous_block_penalty = block_penalty

        if block_penalty <= previous_block_penalty:
            best_producer = producer_ip

    return best_producer


if __name__ == "__main__":
    logger = get_logger(file="block_ops.log")
    load_block_producers()
    block_ip = get_config()["ip"]
    address = load_keys()["address"]
    # rollback_one_block()
    no_of_blocks = 1
    for _ in range(0, no_of_blocks):
        latest_block_info = get_latest_block_info(logger=logger)

        block_message = construct_block(
            logger=logger,
            block_number=latest_block_info["block_number"] + 1,
            parent_hash=latest_block_info["block_hash"],
            block_ip=block_ip,
            creator=address,
            transaction_pool=get_transaction_pool_demo(),
            block_producers_hash=get_block_producers_hash_demo(),
            block_reward=get_block_reward(logger=logger),
        )

        print(block_message)

        """submit as block candidate"""
        config = get_config()
        ip = config["ip"]
        port = config["port"]
        server_key = config["server_key"]
        requests.get(f"http://{ip}:{port}/submit_block?data={json.dumps(block_message)}&key={server_key}", timeout=3)
