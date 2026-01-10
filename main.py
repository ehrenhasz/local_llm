# main.py - Main entry point for the refactored local_llm application
import os
import sys
from src import ai_mode, crypto_mode

def show_menu():
    """Clears the console and displays the main menu."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==================================")
    print("   local_llm Controller (Python)")
    print("==================================")
    print("1. AI Mode")
    print("2. Crypto Mode")
    print("Q. Quit")

def main():
    """Main application loop."""
    while True:
        show_menu()
        selection = input("Please make a selection: ").strip().lower()

        if selection == '1':
            print("\nStarting AI Mode...")
            ai_mode.start()
            input("Press Enter to continue...")
        elif selection == '2':
            print("\nStarting Crypto Mode...")
            crypto_mode.start()
            input("Press Enter to continue...")
        elif selection == 'q':
            print("Exiting...")
            sys.exit(0)
        else:
            print(f"\nInvalid selection: '{selection}'")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
