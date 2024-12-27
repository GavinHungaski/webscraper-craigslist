from ui import *
import logging


def initialize():
    logging.basicConfig(filename='./data/ErrorLog.log', level=logging.ERROR)
    files_to_create = ['./links.txt', './discord.txt',
                       './data/seen_listings.txt']
    for file in files_to_create:
        try:
            with open(file, 'x') as _:
                pass
        except FileExistsError:
            pass


def main():
    initialize()
    root = tk.Tk()
    _ = ScraperUI(master=root)
    root.mainloop()


if __name__ == "__main__":
    main()
