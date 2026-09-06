import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.spatial.distance import euclidean

"""
Workflow:
want to instantiate PCA Util and fit it to a data set and get 
"""
class PCA_Util:
    def __init__(self, n_components:int|None=None):
        self.pca = PCA(n_components=n_components)
        self.scalar = StandardScaler()
        self.feature_names = []

    def fit(self, pk_dex_table: pd.DataFrame) -> pd.DataFrame:
        """Fit the scaler and PCA, return transformed data."""

        # record the data coming in
        self.pokemon_name = pk_dex_table.pokemon_name

        X = pk_dex_table.drop(columns="pokemon_name")
        self.df = X
        self.feature_names = X.columns.tolist()

        # transform X
        scaled_X = self.scalar.fit_transform(X)

        self.pca.fit(scaled_X)
        scaled_X = self.pca.transform(scaled_X)

        # put it back into the same format as expected
        n_components = scaled_X.shape[1]
        self.scaled_X = pd.DataFrame(scaled_X, columns=[f"PC{i+1}" for i in range(n_components)])
        self.scaled_X["pokemon_name"] = self.pokemon_name

        return self.scaled_X

    def inverse_transform(self, pca_coords: pd.DataFrame) -> pd.DataFrame:
        """Go from PCA space back to original feature space."""

        if "pokemon_name" in pca_coords.columns.tolist():
            pca_coords = pca_coords.drop("pokemon_name")

        scaled_coords = self.pca.inverse_transform(pca_coords)
        original_coords = self.scalar.inverse_transform(scaled_coords)
        return pd.DataFrame(original_coords, columns=self.feature_names)


    def print_loadings(self) -> dict[str,dict[str, float]]:
        # detailed breakdown of each PC
        returned_loadings = {}
        for pc_idx, loadings in enumerate(self.pca.components_):
            feature_loadings = list(zip(self.feature_names, loadings))
            print(f"\nPC{pc_idx + 1} ({self.pca.explained_variance_ratio_[pc_idx]:.1%} variance):")
            # print(feature_loadings)
            
            # # Optional: sort by absolute loading (strongest contributors first)
            # sorted_loadings = sorted(feature_loadings, key=lambda x: abs(x[1]), reverse=True)
            # print(f"PC{pc_idx + 1} (sorted by strength):")
            loading_dict = {}
            for feature, loading in feature_loadings:
                print(f"  {feature}: {loading:.4f}")
                loading_dict[feature] = loading

            returned_loadings[f"PC{pc_idx + 1}"] = loading_dict

        return returned_loadings

    def scree_plot(self) -> tuple:
        # explained varience plots for feature reduction
        explained_variance = self.pca.explained_variance_ratio_
        cumulative_variance = np.cumsum(explained_variance)

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Individual variance
        sns.barplot(x=range(1, len(explained_variance) + 1), 
                    y=explained_variance, 
                    ax=axes[0])
        axes[0].set_xlabel('Principal Component')
        axes[0].set_ylabel('Explained Variance Ratio')
        axes[0].set_title('Individual Explained Variance')

        # Cumulative variance
        sns.lineplot(x=range(1, len(cumulative_variance) + 1), 
                    y=cumulative_variance, 
                    marker='o', 
                    ax=axes[1],
                    linewidth=2)
        axes[1].axhline(y=0.95, color='r', linestyle='--', label='95% Variance')
        axes[1].set_xlabel('Number of Components')
        axes[1].set_ylabel('Cumulative Explained Variance')
        axes[1].set_title('Cumulative Explained Variance')
        axes[1].legend()
        axes[1].grid(True, alpha=.5)

        plt.tight_layout()
        plt.show()

        return fig, axes

    def heat_map(self):
        # loadings heatmap

        loadings = self.pca.components_.T * np.sqrt(self.pca.explained_variance_)
        loadings_df = pd.DataFrame(
            loadings,
            columns=[f'PC{i+1}' for i in range(loadings.shape[1])],
            index=self.feature_names
        )

        plt.figure(figsize=(10,6))
        sns.heatmap(loadings_df, annot=True, fmt='.2f', 
                    cmap='coolwarm', center=0, cbar_kws={'label': 'Loading'})
        plt.title('PCA Loadings: How Original Features Contribute to Each PC', 
                fontsize=13, fontweight='bold')
        plt.ylabel('Original Features', fontsize=12)
        plt.xlabel('Principal Components', fontsize=12)
        plt.tight_layout()
        plt.show()

    def biplot(self, PC_0: int=0, PC_1: int=1, **kwargs):
        fig, ax = plt.subplots(figsize=(4, 4))

        # Plot data points
        scatter = ax.scatter(self.scaled_X.iloc[:, PC_0], self.scaled_X.iloc[:, PC_1], 
                            alpha=0.6, s=100, 
                            edgecolors='black', linewidth=0.5)

        # Add feature vectors
        for i, feature in enumerate(self.feature_names):
            ax.arrow(0, 0, 
                    self.pca.components_[PC_0, i] * 3, 
                    self.pca.components_[PC_1, i] * 3,
                    head_width=0.15, head_length=0.15, fc='red', ec='darkred', alpha=0.7)
            ax.text(self.pca.components_[PC_0, i] * 3.3, self.pca.components_[PC_1, i] * 3.3, 
                    feature, fontsize=11, fontweight='bold', 
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_xlabel(f'PC{PC_0 + 1} ({self.pca.explained_variance_ratio_[PC_0]:.1%} variance)', 
                    fontsize=12, fontweight='bold')
        ax.set_ylabel(f'PC{PC_1 + 1} ({self.pca.explained_variance_ratio_[PC_1]:.1%} variance)', 
                    fontsize=12, fontweight='bold')
        ax.set_title('PCA Biplot: Data Points and Feature Contributions', 
                    fontsize=13, fontweight='bold')
        ax.grid(alpha=0.3)
        ax.axhline(y=0, color='k', linewidth=0.5)
        ax.axvline(x=0, color='k', linewidth=0.5)

        plt.tight_layout()
        plt.show()