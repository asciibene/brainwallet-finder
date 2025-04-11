import hashlib
import ecdsa
import base58
import requests
import os
import json
import time
from eth_account import Account 
import re 
from urllib.request import urlopen
from time import sleep
from colorama import init, Fore, Style
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from ratelimit import limits, sleep_and_retry
from sys import argv


# Initialize colorama
init(autoreset=True)


# Constants

os.environ['ECC_BACKEND_CLASS'] = 'eth_keys.backends.NativeECCBackend'

RATE_LIMIT = 3# Max 1 request per second
TIME_PERIOD = 1  # Time period in seconds for rate limit
WEI_PER_ETH = 1e10

ES_KEY= "RJWQE7MKV6FCSGP41N8YHNMKJ9VATFN8ZD"
ES_CHAINIDS={"etherscan":1 , 'ftmscan': 250, 'optimistic': 10, 'polygon': 137, 'arbitrum': 42161, 'gnosis': 100,'base': 8453,'avalanche': 43114,'zkSync': 324}
   
CHECK_TOKENS = False #TODO
TOKEN_CONTRACTS = {"name", 'hexaddr'}


# Adjust the check_balance function
@sleep_and_retry
@limits(calls=RATE_LIMIT, period=TIME_PERIOD)
def check_address_balance_eth(address,privkey): 
    try:
        wallets_multichain=[]
        for chain,chainid in tqdm(ES_CHAINIDS.items(), colour='blue'):
            #Todo : send multiple address in 1 query.. use  |
            url= f"https://api.etherscan.io/v2/api?chainid={chainid}&module=account&action=balance&address={address}&tag=latest&apikey={ES_KEY}"
            htmltext = urlopen(url, timeout=6).read().decode('utf-8')
            if htmltext is None: raise("Empty reply from url")
            
            dat=json.loads(htmltext)
            #ethscan_info = {t: float(re.search(rf'{t}":"(\d+)', htmltext).group(1)) for t in etherscan_tags}print(dat)
           # dat['result'] = float(dat['result']) /  WEI_PER_ETH
            del dat['status'] 
            #dat['result'] = float(dat['result'])
            dat['message'] = Fore.GREEN + dat['message'] + Style.RESET_ALL if dat['message'] == 'OK' else exit() 

            dat['chain']=f"{chain} ({chainid})" 
            dat['address'] = address
            dat['private_key'] = privkey
            wallets_multichain.append(dat)
            time.sleep(0.05)
        return wallets_multichain
    except Exception as e:
        print(f"Request failed for address {address}: {e}")
        return None



def gen_wallet_eth():
    wallet = Account.create()
    return wallet.key.hex(), wallet.address

def process_iteration():
    private_key, address = gen_wallet_eth()
    if not private_key or not address:
        raise(Error)
    
    wallets_info = check_address_balance_eth(address,private_key)
    #wallet_info['address']=address
    #wallet_info['priv_key']=private_key'

    return wallets_info

def save_results(output_file,wallet_info):
    try:
        with open(output_file, 'a+') as f_out:
            f_out.write(f"=======   ETH    =============")
            for key, val in wallet_info.items():
                f_out.write(f"{key}: {val}\n")
            f_out.write("==============================\n")
    except IOError as e:
        we_got_problems=True
        print(f"Failed to write results to {output_file}: {e}")


def main():
    output_file = os.getenv('OUTPUT_FILE', 'wallets_with_balance.txt')
    num_workers = int(os.getenv('NUM_WORKERS', 1))
    #passphrases = load_passphrases(input_file)
    addrs_with_bal = []
    we_got_problems=False
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        MAX_ITER = int(argv[1]) or 250

        future_to_iter = {executor.submit(process_iteration): i for i in range(1,MAX_ITER)}
        found_wallets = 0
        for future in as_completed(future_to_iter): 
            try:
                wallets = future.result()
                for w in wallets:
                    if float(w['result']) > 0:
                        status = Fore.GREEN + "ACTIVE!" + Style.RESET_ALL
                        save_results(output_file,w)
                        found_wallets += 1
                    else:
                        status = Fore.RED + "DEAD" + Style.RESET_ALL
                    
                    # Print the details with status
                    print(Fore.BLUE + f'Wallet data >>> {w["chain"]}' + Style.RESET_ALL )
                    for key, val in w.items():
                        if key == "result" and int(val) > 0:
                            key = Fore.CYAN + key + Style.RESET_ALL
                            val = Back.YELLOW + Fore.MAGENTA + val + Style.RESET_ALL

                        print(f"{key}: {val}")
                    print(f"Status: {status}")
                print((Fore.RED + "We have got an error.." + Style.RESET_ALL ) if we_got_problems else "")

            except Exception as e:
                print(f"Main Program Loop failed :  {e}")
                we_got_problems = True

    print(f"Processing complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()
