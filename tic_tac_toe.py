

def display_board(board):
    """Display the 3x3 game board."""
    print()
    print(f" {board[0]} | {board[1]} | {board[2]} ")
    print("---+---+---")
    print(f" {board[3]} | {board[4]} | {board[5]} ")
    print("---+---+---")
    print(f" {board[6]} | {board[7]} | {board[8]} ")
    print()


def check_winner(board, mark):
    """Return True if the given mark has three in a row."""
    winning_combinations = [
        (0, 1, 2),  # Top row
        (3, 4, 5),  # Middle row
        (6, 7, 8),  # Bottom row
        (0, 3, 6),  # Left column
        (1, 4, 7),  # Middle column
        (2, 5, 8),  # Right column
        (0, 4, 8),  # Main diagonal
        (2, 4, 6),  # Other diagonal
    ]

    for a, b, c in winning_combinations:
        if board[a] == board[b] == board[c] == mark:
            return True
    return False


def get_move(board, player_name, mark):
    """Ask for a valid cell number and return its board index."""
    while True:
        choice = input(
            f"{player_name} ({mark}), enter a cell number (1-9): "
        ).strip()

        if choice == "":
            print("Input cannot be empty. Please try again.")
            continue

        try:
            cell = int(choice)
        except ValueError:
            print("Invalid input. Please enter a number from 1 to 9.")
            continue

        if cell < 1 or cell > 9:
            print("Out of range. Choose a number from 1 to 9.")
            continue

        index = cell - 1
        if board[index] in ("X", "O"):
            print("That cell is already occupied. Choose another cell.")
            continue

        return index


def play_game(player1, player2):
    """Run one round of Tic-Tac-Toe and return the winning mark or None."""
    board = [str(number) for number in range(1, 10)]
    players = [(player1, "X"), (player2, "O")]
    turn = 0

    print("\nCell positions:")
    display_board(board)

    while True:
        player_name, mark = players[turn]
        index = get_move(board, player_name, mark)
        board[index] = mark
        display_board(board)

        if check_winner(board, mark):
            print(f"Congratulations, {player_name} ({mark}) wins!")
            return mark

        if all(cell in ("X", "O") for cell in board):
            print("It's a draw!")
            return None

        turn = 1 - turn


def main():
    """Start the game and manage replay and scores."""
    print("=" * 35)
    print("       TIC-TAC-TOE GAME")
    print("=" * 35)

    player1 = input("Enter Player 1 name (X): ").strip() or "Player 1"
    player2 = input("Enter Player 2 name (O): ").strip() or "Player 2"

    scores = {player1: 0, player2: 0}
    draws = 0

    while True:
        result = play_game(player1, player2)

        if result == "X":
            scores[player1] += 1
        elif result == "O":
            scores[player2] += 1
        else:
            draws += 1

        print("\nScoreboard")
        print("-" * 20)
        print(f"{player1} (X): {scores[player1]}")
        print(f"{player2} (O): {scores[player2]}")
        print(f"Draws: {draws}")

        while True:
            again = input("\nWould you like to play again? (yes/no): ").strip().lower()
            if again in ("yes", "y"):
                break
            if again in ("no", "n"):
                print("\nThanks for playing Tic-Tac-Toe. Goodbye!")
                return
            print("Please enter yes or no.")


if __name__ == "__main__":
    main()
