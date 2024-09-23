import re
from datetime import datetime

from dotenv import dotenv_values

env_variables = dotenv_values(".env")


class HandHistoryParser:
    def __init__(self, file_path, player):
        self.file_path = file_path
        self.hands = []
        self.player = player

    def parse(self):
        with open(self.file_path, "r") as file:
            hand_data = []
            for line in file:
                line = line.strip()  # Remove leading/trailing whitespace

                # If we reach an empty line or "*** SUMMARY ***", this indicates the end of a hand
                if line == "" or line.startswith("*** SUMMARY ***"):
                    if hand_data:
                        self.hands.append(self.parse_hand(hand_data))
                        hand_data = []  # Reset for the next hand
                else:
                    hand_data.append(line)  # Collect lines for the current hand

            # Catch the last hand if the file doesn't end with an empty line or "SUMMARY"
            if hand_data:
                self.hands.append(self.parse_hand(hand_data))

    def parse_hand(self, hand_data):
        hand_info = {}
        hand_info["players"] = []
        hand_info["actions"] = []
        hand_info["board"] = []
        button_seat = None
        player_seats = []
        player_cards = None  # To store the cards of the player

        for line in hand_data:
            # Debugging
            print(f"Parsing line: {line}")

            # 1. Parse Hand ID, Tournament ID, and Date
            if line.startswith("PokerStars Hand #"):
                hand_info["hand_id"] = re.search(r"Hand #(\d+)", line).group(1)
                hand_info["tournament_id"] = re.search(
                    r"Tournament #(\d+)", line
                ).group(1)
                hand_info["date"] = datetime.strptime(
                    re.search(r"- (\d+/\d+/\d+ \d+:\d+:\d+)", line).group(1),
                    "%Y/%m/%d %H:%M:%S",
                )

            # 2. Parse Table Info and Button Seat
            elif line.startswith("Table '"):
                hand_info["table"] = re.search(r"Table '([^']+)'", line).group(1)
            elif line.startswith("Seat #"):
                button_seat = int(
                    re.search(r"Seat #(\d+) is the button", line).group(1)
                )
                print(f"Button is at seat: {button_seat}")

            # 3. Parse Player Info (with optional bounty)
            elif line.startswith("Seat "):
                player_info = re.search(
                    r"Seat (\d+): ([^\(]+) \((\d+) in chips(?:, €([\d\.]+) bounty)?\)",
                    line,
                )
                if player_info:
                    seat_number = int(player_info.group(1))
                    self.player = player_info.group(2).strip()
                    chips = int(player_info.group(3))
                    bounty = (
                        float(player_info.group(4)) if player_info.group(4) else 0.0
                    )

                    player_data = {
                        "name": self.player,
                        "chips": chips,
                        "bounty": bounty,
                        "seat": seat_number,
                    }

                    hand_info["players"].append(player_data)
                    player_seats.append(seat_number)

            # 4. Parse Player Actions
            elif re.match(r"\w+: ", line):
                action_info = re.match(r"(\w+): (.*)", line)
                if action_info:
                    hand_info["actions"].append(
                        {"player": action_info.group(1), "action": action_info.group(2)}
                    )

            # 5. Parse hole cards dealt to 'player_cards'
            elif re.match(r"Dealt to {env_variables['PLAYER_NAME']} \[(.+)\]", line):
                player_cards = re.findall(r"\[([^\]]+)\]", line)[0]
                print(f"{self.player} has hole cards: {player_cards}")

            # 6. Parse Board Cards (Flop, Turn, River)
            elif line.startswith("*** FLOP ***"):
                hand_info["board"] += re.findall(r"\[([^\]]+)\]", line)[0].split()
            elif line.startswith("*** TURN ***") or line.startswith("*** RIVER ***"):
                hand_info["board"].append(re.findall(r"\[([^\]]+)\]", line)[0])

        # 7. Assign Player Positions Relative to the Button
        if button_seat:
            hand_info["players"] = self.assign_positions(
                hand_info["players"], button_seat
            )

        # 8. Add player_cards cards to the corresponding player
        for player in hand_info["players"]:
            if player["name"] == self.player:
                player["hole_cards"] = (
                    player_cards if player_cards else "No cards dealt"
                )
                print(f"Assigned hole cards to {self.player}: {player['hole_cards']}")

        return hand_info

    def assign_positions(self, players, button_seat):
        """
        Assigns the position relative to the button for each player.
        Positions are labeled as Button, Button+1, Button+2, etc.
        """
        sorted_players = sorted(players, key=lambda x: x["seat"])
        num_players = len(sorted_players)

        # Find the index of the button
        button_index = next(
            i
            for i, player in enumerate(sorted_players)
            if player["seat"] == button_seat
        )

        # Assign positions relative to the button
        for i, player in enumerate(sorted_players):
            relative_position = (i - button_index) % num_players
            position_label = (
                "Button" if relative_position == 0 else f"Button+{relative_position}"
            )
            player["position"] = position_label

        return sorted_players
