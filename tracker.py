import tkinter as tk #Gui
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt #To plot line charts
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # to implement it into tkinter
import requests
import threading
from datetime import datetime
import pandas as pd

#Fetch crypto from CoinGecko API
def get_crypto_list():
    url = 'https://api.coingecko.com/api/v3/coins/list'
    response = requests.get(url, timeout =1)
    return response.json()

#Fetch crypto price data from Coin Gecko
def fetch_crypto_data(crypto_ids):
    url = f'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency' : 'usd',
        'ids': ','.join(crypto_ids),
        'order': 'market_cap_desc',
        'per_page': 250,
        'page': 1
    }
    response = requests.get(url, params= params, timeout = 1)
    return response.json()

#Fetch historical price data from Coin Gecko
def fetch_historical_data(crypto_ids):
    all_data = {}
    for crypto_id in crypto_ids:
        url = f'https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart'
        params = {'vs_currency': 'usd', 'days': '7'}
        response = requests.get(url, params=params, timeout=1)

        if response.status_code != 200:
            print(f"API Error for {crypto_id}: {response.status_code}, {response.text}")
            continue  # Skip this crypto and proceed to the next

        data = response.json()

        if 'prices' not in data:
            print(f"Error: 'prices' not found for {crypto_id}. Response: {data}")
            continue  # Skip this crypto and proceed to the next

        rows = data['prices']
        dates = []
        prices = []

        for row in rows:
            timestamp, price = row
            date = datetime.utcfromtimestamp(timestamp / 1000)
            dates.append(date)
            prices.append(price)

        all_data[crypto_id] = {"dates": dates, "prices": prices}

    return all_data

class LoadingPopup:
    def __init__(self, root, message):
        self.top = tk.Toplevel(root)
        self.top.title("Loading...")
        self.top.geometry("300x100")
        self.label = tk.Label(self.top, text=message)
        self.label.pack(pady=10)
        self.progress = ttk.Progressbar(self.top, orient='horizontal', mode='indeterminate', length=280)
        self.progress.pack(pady=10)
        self.progress.start()

    def destroy(self):
        self.progress.stop()
        self.top.destroy()


class CryptoTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cryptocurrency Tracker")

        self.create_widgets()
        self.crypto_list = pd.DataFrame([])

        #Start loading the data from the API in a seperate thread
        threading.Thread(target=self.load_crypto_data).start()

    def load_crypto_data(self):
        loading_popup = LoadingPopup(self.root, "Loading Cryptocurrency Data...")
        self.crypto_list = pd.DataFrame(get_crypto_list())
        self.update_search_results()

        self.crypto_listbox.grid(row=2, column=0)
        loading_popup.destroy()

    def create_widgets(self):
        tk.Label(self.root, text="Search Crypto's To Track").grid(row=0, column=0, padx=5, pady=5)
        self.search_var = tk.StringVar()
        self.search_bar = tk.Entry(self.root, textvariable=self.search_var, width=50)
        self.search_bar.grid(row=1, column=0, padx=5, pady=5)
        self.search_bar.bind('<KeyRelease>', lambda event: self.update_search_results())

        self.crypto_listbox = tk.Listbox(self.root, selectmode='multiple', width=50, height=20)
        self.crypto_listbox.grid_forget()

        self.select_button = tk.Button(self.root, text="Select Cryptos", command=self.select_cryptos)
        self.select_button.grid(row=3, column=0)

        tk.Label(self.root, text="Selected Crypto's").grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.root, text="The Crypto's shown below are currently being tracked!").grid(row=1, column=1, padx=5, pady=5)

        self.selected_cryptos_listbox = tk.Listbox(self.root, selectmode='multiple', width=50, height=20)
        self.selected_cryptos_listbox.grid(row=2, column=1, padx=5)
        self.load_selected_cryptos()

        self.track_button  = tk.Button(self.root, text="Track Cryptos", command=self.track_cryptos, state='normal')
        self.track_button.grid(row=3, column=1, pady=5)

        self.delete_button = tk.Button(self.root, text="Delete Selected Cryptos", command=self.delete_selected_cryptos)
        self.delete_button.grid(row=4, column=1, pady=5)

    def update_search_results(self):
        search_term  = self.search_var.get().lower()

        self.crypto_listbox.delete(0, tk.END)

        filtered_cryptos = self.crypto_list.query(f"name.str.lower().str.startswith('{search_term}')")

        for i, filtered_crypto in filtered_cryptos.iterrows():
            self.crypto_listbox.insert(tk.END, filtered_crypto['symbol'].upper() + " - " + filtered_crypto['name'] + " - " + filtered_crypto['id'])

    def select_cryptos(self):
        selected_indices = self.crypto_listbox.curselection()
        selected_cryptos = [self.crypto_listbox.get(selected_indice) for selected_indice in selected_indices]

        if not selected_cryptos:
            messagebox.showwarning("No Selection", "Please select at least one crypto")
            return

        for selected_crypto in selected_cryptos:
            self.selected_cryptos_listbox.insert(tk.END, selected_crypto)

        all_selected_cryptos = self.selected_cryptos_listbox.get(0, tk.END)
        selected_crypto_ids  = [selected_crypto.split(' - ')[-1].strip() for selected_crypto in all_selected_cryptos]
        df_selected_cryptos  = self.crypto_list.query(f"id.isin({selected_crypto_ids})")
        self.selected_crypto_ids = df_selected_cryptos['id'].to_list()
        df_selected_cryptos.to_csv('./selected_cryptos.csv',index=False)
        

    def load_selected_cryptos(self):
        try:
            selected_cryptos = pd.read_csv('./selected_cryptos.csv')
            self.selected_crypto_ids = selected_cryptos['id'].to_list()

            for i, selected_crypto in selected_cryptos.iterrows():
                self.selected_cryptos_listbox.insert(tk.END, selected_crypto['symbol'].upper() + " - " + selected_crypto['name'] + " - " + selected_crypto['id'])

        except Exception as e:
            return

    def delete_selected_cryptos(self):
        selected_indices = self.selected_cryptos_listbox.curselection()

        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one crypto to delete")
            return
        
        for index in reversed(selected_indices):
            self.selected_cryptos_listbox.delete(index)

        #Updating the CSV File
        remaining_cryptos = self.selected_cryptos_listbox.get(0, tk.END)
        remaining_crypto_ids = [crypto.split(' - ')[-1].strip() for crypto in remaining_cryptos]
        df_remaining_cryptos = self.crypto_list.query(f"id.isin({remaining_crypto_ids})")
        self.selected_crypto_ids = df_remaining_cryptos['id'].to_list()
        df_remaining_cryptos.to_csv('./selected_cryptos.csv', index=False)

    def track_cryptos(self):
        #Fetch the data for the selected cryptos 
        self.crypto_data = fetch_historical_data(self.selected_crypto_ids)
        self.show_crypto_performance()

    def show_crypto_performance(self):
        self.visuals_screen = tk.Toplevel(self.root)

        if hasattr(self, 'fig'):
            self.fig.clear()

        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().pack_forget()

        table_headings = ["Coin", "Current Price", "High 24H", "Low 24H", "Price Change 24H", "All Time High", "All Time Low"]
        keys           = ['name', 'current_price','high_24h', 'low_24h', 'price_change_24h', 'ath', 'atl']

        self.crypto_overview_data = fetch_crypto_data(list(self.crypto_data.keys()))
        self.table = ttk.Treeview(self.visuals_screen, columns=table_headings, show='headings')

        for table_heading in table_headings:
            self.table.heading(table_heading, text=table_heading)

        for row in self.crypto_overview_data:
            self.table.insert("", tk.END, values=[
                "$" + str(row[key]) if isinstance(row[key] , (int, float)) else str(row[key])
                for key in keys
            ])

        self.table.pack()

        self.fig, ax = plt.subplots()
        for crypto_id in self.crypto_data.keys():
            ax.plot(self.crypto_data[crypto_id]['dates'], self.crypto_data[crypto_id]['prices'], label=f"{crypto_id}")

        ax.set_title("Crypto Performance Over the last 7 Days")
        ax.set_xlabel("Days")
        ax.set_ylabel("Price (USD)")
        ax.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.visuals_screen)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=True)

import time

def fetch_historical_data(crypto_ids):
    all_data = {}

    for crypto_id in crypto_ids:
        attempts = 0
        success = False

        while attempts < 3 and not success:
            url = f'https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart'
            params = {
                'vs_currency': 'usd',
                'days': '7'
            }

            response = requests.get(url, params=params, timeout=1)
            if response.status_code == 200:
                data = response.json()
                if 'prices' in data:
                    rows = data['prices']
                    dates = []
                    prices = []

                    for row in rows:
                        timestamp, price = row
                        date = datetime.utcfromtimestamp(timestamp / 1000)
                        dates.append(date)
                        prices.append(price)

                    all_data[crypto_id] = {"dates": dates, "prices": prices}
                    success = True
                else:
                    print(f"Error: 'prices' not found for {crypto_id}. Response: {data}")
            else:
                print(f"Failed to fetch data for {crypto_id}: {response.status_code}")
                attempts += 1
                time.sleep(2)  # Wait before retrying

    return all_data



root = tk.Tk()
app = CryptoTrackerApp(root)
root.mainloop()
