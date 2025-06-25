# Learning to Rank model for move ordering

# import tensorflow
import os

import lightgbm
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.chess_bot import DATASET_FILE_PATH, ChessBot, generate_features


def train_ltr_model(data_load_path: str, model_save_path: str):
    # Preprocess the dataset
    data = pd.read_csv(data_load_path)

    # Normalize features to hold same relative weight in decision making
    features = data.drop(columns=["group_id", "move", "is_best_move"])
    features.drop(
        columns=[
            "is_checkmate",
            "is_draw",
            # "castling",
            # "attack_undefended",
            # "center_control",
        ],
        inplace=True,
        errors="ignore",
    )  # Drop columns with less significant model importance

    scaler = StandardScaler()
    normalized_features = pd.DataFrame(
        scaler.fit_transform(features), columns=features.columns
    )

    labels = data["is_best_move"]
    group = (
        data.groupby("group_id").size().to_list()
    )  # Group is the length of data in each group and assumes ordering

    # Train the model
    dataset = lightgbm.Dataset(data=normalized_features, label=labels, group=group)

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",  # Normalized Discounted Cumulative Gain
        "boosting_type": "gbdt",  # Gradient Boosted Decision Tree
        "learning_rate": 0.02,
        "num_leaves": 16,
        "min_data_in_leaf": 32,
        "lambda_l2": 10.0,  # L2 regularization
        "verbose": 1,
    }

    model = lightgbm.train(params, dataset, num_boost_round=200)

    model.save_model(model_save_path)


class LTRChessBotTrainer(ChessBot):
    def __init__(self, response, client):
        super().__init__(response, client)

    def adversarial_search(self):
        """Overrides parent method to add saving of moves"""
        # Set up a path to save data to for later analysis
        print("Saving data at:", DATASET_FILE_PATH)
        os.makedirs(os.path.dirname(DATASET_FILE_PATH), exist_ok=True)

        # Get the last group id from previous recordings
        try:
            temp_df = pd.read_csv(DATASET_FILE_PATH)
            group_id = temp_df["group_id"].max()
        except:
            group_id = 0  # or None, depending on your needs

        while self.is_active:
            # Wait for opponent's move
            if not self.wait_for_move_event():
                return

            print("Evaluating with default engine!")
            best_move = self.engine.get_best_move(self.board)  # Find the best move
            print("Evaluating with LTR engine!")
            best_move = self.ltr_engine.get_best_move(self.board)  # Find the best move

            group_id += 1
            for move in list(self.board.legal_moves):
                # Generate set of features for each move
                data_entry = generate_features(
                    self.board, move, self.engine.player_color
                )

                # Add label info for board state group, move, and classificiation for whether it was the best move
                data_entry["group_id"] = group_id
                data_entry["move"] = move
                data_entry["is_best_move"] = move == best_move

                # Save move data to dataset for later analysis
                data_entry.to_csv(
                    DATASET_FILE_PATH,
                    mode="a",
                    header=not os.path.exists(DATASET_FILE_PATH),
                    index=False,
                )

            self.best_move_message_queue.put(best_move.uci())  # Convert move to string
            self.move_made_event.clear()


def main():
    data_load_path = r"src\data\LTR_trainer_dataset.csv"
    model_save_path = r"src\LTR_model.txt"
    train_ltr_model(data_load_path, model_save_path)


def feature_analysis(model_save_path):
    model = lightgbm.Booster(model_file=model_save_path)
    importances = [float(i) for i in model.feature_importance(importance_type="gain")]
    feature_names = model.feature_name()

    feature_weights = pd.Series(dict(zip(feature_names, importances))).sort_values()
    print(feature_weights)


if __name__ == "__main__":
    main()
    feature_analysis()
