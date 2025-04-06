import hashlib
import ecdsa
import base58
import requests
import logging
import os
import time
from eth_account import Account
import re
from urllib.request import urlopen
from time import sleep
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from ratelimit import limits, sleep_and_retry

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
RATE_LIMIT = 1 # Max 1 request per second
TIME_PERIOD = 10  # Time period in seconds for rate limit
SATOSHIS_PER_BITCOIN = 1e8

blockchain_tags = ['total_received', 'final_balance','n_tx']

# Adjust the check_balance function
@sleep_and_retry
@limits(calls=RATE_LIMIT, period=TIME_PERIOD)
def check_api_btc(address): 
    try:
        #Todo : send multiple address in 1 query.. use  |
        url = f"https://blockchain.info/rawaddr/{address}"
        start_time = time.time()
        htmlfile = urlopen(url, timeout=10)
        end_time = time.time()
        ping = end_time - start_time
        htmltext = htmlfile.read().decode('utf-8')

        blockchain_info = {t: float(re.search(rf'{t}":(\d+)', htmltext).group(1)) for t in blockchain_tags}
        
        blockchain_info['final_balance'] /= SATOSHIS_PER_BITCOIN
        blockchain_info['ping'] = ping
        return blockchain_info
    except Exception as e:
        print(f"Request failed for address {address}: {e}")
        return None

def gen_wallet_btc(passphrase):
    try:
        private_key = hashlib.sha256(passphrase.encode('utf-8')).digest()
        sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        public_key = b'\x04' + vk.to_string()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(hashlib.sha256(public_key).digest())
        hashed_public_key = ripemd160.digest()
        checksum = hashlib.sha256(hashlib.sha256(b'\x00' + hashed_public_key).digest()).digest()[:4]
        address = base58.b58encode(b'\x00' + hashed_public_key + checksum)
        return private_key.hex(), address.decode()
    except Exception as e:
        logging.error(f"Failed to generate wallet for passphrase {passphrase}: {e}")
        return None, None

def gen_wallet_eth(passphrase):
    wallet = Account.create(passphrase)
    return wallet.key, wallet.address

def check_api_eth(address):
    url = f"https://blockchain.info/rawaddr/{address}"
    start_time = time.time()
    htmlfile = urlopen(url, timeout=10)
    end_time = time.time()
    ping = end_time - start_time
    htmltext = htmlfile.read().decode('utf-8')

    blockchain_info = {t: float(re.search(rf'{t}":(\d+)', htmltext).group(1)) for t in blockchain_tags}
 


def process_passphrase(passphrase):
    private_key, address = gen_wallet_btc(passphrase)
    if not private_key or not address:
        raise(Error)
    
    btc_wallet_info = check_api_btc(address)
    btc_wallet_info['address']=address
    btc_wallet_info['priv_key']=private_key
    
    #TODO same but for eth and others
    
    return btc_wallet_info


def load_passphrases(input_file):
    try:
        with open(input_file, 'r') as f:
            passphrases = [line.strip() for line in f]
            return passphrases
    except FileNotFoundError:
        print(f"Input file {input_file} not found.")
        return None

def save_results(output_file,wallet_info,token):
    try:
        with open(output_file, 'a') as f_out:
            f_out.write(f"======= {token} =============")
            for key, val in wallet_info:
                f_out.write(f"{key}: {val}\n")
            f_out.write("==============================\n")
    except IOError as e:
        print(f"Failed to write results to {output_file}: {e}")


def main():
    input_file = os.getenv('INPUT_FILE', 'passphrases.txt')
    output_file = os.getenv('OUTPUT_FILE', 'wallets_with_balance.txt')
    num_workers = int(os.getenv('NUM_WORKERS', 10))

    passphrases = load_passphrases(input_file)
    if not passphrases:
        raise("No passphrases to process.")

    addrs_with_bal = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_passphrase = {executor.submit(process_passphrase, passphrase): passphrase for passphrase in passphrases}

        for future in tqdm(as_completed(future_to_passphrase), total=len(passphrases), desc="Processing passphrases"): 
            try:
                btc_info = future.result()
                
                #TODO do same check for all wallet types
                if balance > 0:
                    status = Fore.GREEN + "ACTIVE!" + Style.RESET_ALL
                    save_results(output_file,addr_info)
                else:
                    status = Fore.RED + "DEAD" + Style.RESET_ALL
                
                # Print the details with status
                print('Bitcoin Wallet data >>> -------------')
                for key, val in btc_info.items():
                    print(f"{key}: {val}")
                print(f"Status: {status}")
                
                print('Ethereum Wallet data >>> -----------')
                
                
                print()
            except Exception as e:
                logging.error(f"Future processing failed: {e}")

    logging.info(f"Processing complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()
