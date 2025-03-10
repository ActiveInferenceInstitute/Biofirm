"""
Visualization methods for OneEarth Bioregion Analysis.
This module contains functions for data preprocessing, analysis, and visualization.
"""

import os
import re
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
# Wrap sklearn imports in try-except blocks to handle cases when it's not installed
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import PCA, TruncatedSVD
    from sklearn.manifold import TSNE
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    # Create dummy classes to avoid crashes when sklearn is not available
    class DummyModel:
        def __init__(self, *args, **kwargs):
            pass
        def fit_transform(self, *args, **kwargs):
            return np.zeros((1, 2))
        def fit(self, *args, **kwargs):
            return self
        def transform(self, *args, **kwargs):
            return np.zeros((1, 2))
    
    TfidfVectorizer = DummyModel
    PCA = DummyModel
    TruncatedSVD = DummyModel
    TSNE = DummyModel
    KMeans = DummyModel
    SKLEARN_AVAILABLE = False
    print("WARNING: sklearn is not installed. Some visualization features will be limited.")

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("WARNING: networkx is not installed. Network visualization will be disabled.")

try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False
    print("WARNING: wordcloud is not installed. Word cloud generation will be disabled.")

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("WARNING: plotly is not installed. Interactive visualizations will be disabled.")

import pandas as pd
from pathlib import Path
import logging
from run_pipeline import log_file_operation

# Set up logging
logger = logging.getLogger(__name__)

def read_markdown_files(file_paths):
    """Read content from markdown files."""
    contents = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                contents.append(file.read())
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            contents.append("")  # Add empty string to maintain index alignment
    return contents

def preprocess_text(text, nlp):
    """Preprocess text by removing stopwords, punctuation, and using basic tokenization."""
    # Basic preprocessing
    text = re.sub(r'#\s*', '', text)  # Remove markdown headers
    text = re.sub(r'\*\*|\*', '', text)  # Remove bold/italic markers
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # Remove code blocks
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove links
    text = text.lower()  # Convert to lowercase
    
    # Check if we have a real spaCy NLP object
    if nlp is not None and hasattr(nlp, 'pipe') and callable(getattr(nlp, 'pipe', None)):
        # Process with spaCy if available
        try:
            doc = nlp(text)
            tokens = [token.lemma_.lower() for token in doc 
                    if not token.is_stop and not token.is_punct 
                    and len(token.text.strip()) > 1]
            return ' '.join(tokens)
        except Exception as e:
            logger.warning(f"Error using spaCy for processing: {e}. Falling back to basic processing.")
            # Fall through to basic processing if spaCy fails
    
    # Basic text processing without spaCy
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Remove numbers
    text = re.sub(r'\d+', '', text)
    
    # Simple stopword filtering
    stopwords = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 
                'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 
                'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 
                'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 
                'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 
                'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 
                'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 
                'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 
                'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 
                'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 
                'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 
                'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 
                't', 'can', 'will', 'just', 'don', 'should', 'now'}
    
    # Tokenize and filter
    words = text.split()
    filtered_words = [word for word in words if word not in stopwords and len(word.strip()) > 1]
    
    return ' '.join(filtered_words)

def perform_tfidf_and_dim_reduction(preprocessed_docs, n_components=10, min_df=1, max_df=1.0):
    """Perform TF-IDF vectorization and dimension reduction."""
    if len(preprocessed_docs) < 2:
        logger.warning("Need at least 2 documents for dimension reduction")
        return None, None, None, None, None, None, None
    
    if not SKLEARN_AVAILABLE:
        logger.warning("sklearn not available. Dimension reduction skipped.")
        dummy_matrix = np.zeros((len(preprocessed_docs), 2))
        dummy_vec = TfidfVectorizer()
        return dummy_matrix, dummy_matrix, dummy_matrix, dummy_vec, None, None, None
    
    try:
        # TF-IDF Vectorization with more lenient parameters for small document sets
        vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=min_df,  # Allow terms that appear in just one document
            max_df=max_df   # Allow terms that appear in all documents
        )
        tfidf_matrix = vectorizer.fit_transform(preprocessed_docs)
        
        # Adjust n_components if needed
        n_components = min(n_components, min(tfidf_matrix.shape) - 1)
        n_components = max(2, n_components)  # Ensure at least 2 components
        
        # PCA
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(tfidf_matrix.toarray())
        
        # LSA (Truncated SVD)
        lsa = TruncatedSVD(n_components=n_components)
        lsa_result = lsa.fit_transform(tfidf_matrix)
        
        # t-SNE with adjusted perplexity for small datasets
        perplexity = min(30, max(2, len(preprocessed_docs) - 1))
        tsne = TSNE(n_components=2, perplexity=perplexity)
        tsne_result = tsne.fit_transform(tfidf_matrix.toarray())
        
        return pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne
    except Exception as e:
        logger.error(f"Error in dimension reduction: {e}")
        dummy_matrix = np.zeros((len(preprocessed_docs), 2))
        dummy_vec = TfidfVectorizer()
        return dummy_matrix, dummy_matrix, dummy_matrix, dummy_vec, None, None, None

@log_file_operation
def plot_dimension_reduction(result, labels, color_labels, title, filename, 
                           method_name, vectorizer, model, output_dir):
    """Create 2D scatter plot of dimensionality reduction result."""
    plt.figure(figsize=(12, 10))
    
    # Create a scatter plot
    scatter = plt.scatter(result[:, 0], result[:, 1], c=[hash(label) % 20 for label in color_labels], 
                         cmap='tab20', alpha=0.7, s=100)
    
    # Add labels
    for i, txt in enumerate(labels):
        plt.annotate(txt, (result[i, 0], result[i, 1]), fontsize=9)
    
    plt.title(f"{title} - {method_name}")
    plt.xlabel(f"{method_name} Component 1")
    plt.ylabel(f"{method_name} Component 2")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.colorbar(scatter, label="Document Categories")
    
    # Add legend
    categories = list(set(color_labels))
    category_colors = [hash(label) % 20 for label in categories]
    handles = [plt.Line2D([0], [0], marker='o', color='w', 
                         markerfacecolor=plt.cm.tab20(color), 
                         markersize=10, label=cat) for cat, color in zip(categories, category_colors)]
    plt.legend(handles=handles, title="Categories", loc='best')
    
    # Save figure
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    # Use filename as provided
    file_path = os.path.join(output_dir, filename)
    plt.savefig(file_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved {method_name} plot to {file_path}")

def plot_word_importance(vectorizer, model, method_name, title, filename, output_dir):
    """Plot words with highest importance in the dimensionality reduction."""
    if not hasattr(model, 'components_'):
        logger.warning(f"Model does not have components_ attribute. Skipping word importance for {method_name}.")
        return
        
    feature_names = vectorizer.get_feature_names_out()
    
    plt.figure(figsize=(12, 8))
    
    for i, comp in enumerate(model.components_[:2]):  # Plot first two components
        top_indices = comp.argsort()[-10:]  # Top 10 words
        values = comp[top_indices]
        terms = [feature_names[idx] for idx in top_indices]
        
        plt.subplot(1, 2, i+1)
        plt.barh(terms, values)
        plt.title(f"Top Terms in {method_name} Component {i+1}")
        plt.xlabel("Coefficient Value")
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{filename}_word_importance_{method_name}.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved word importance plot to {file_path}")

@log_file_operation
def plot_pca_eigen_terms(pca, vectorizer, title, filename, output_dir):
    """Plot the top terms contributing to each principal component."""
    feature_names = vectorizer.get_feature_names_out()
    
    plt.figure(figsize=(12, 10))
    components_to_plot = min(4, pca.components_.shape[0])
    
    for i, component in enumerate(pca.components_[:components_to_plot]):
        plt.subplot(2, 2, i + 1)
        indices = component.argsort()[-10:]
        plt.barh([feature_names[j] for j in indices], component[indices])
        plt.title(f'PCA Component {i+1}')
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{filename}_pca_terms.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved PCA eigen terms plot to {file_path}")

@log_file_operation
def create_word_cloud(docs, title, filename, output_dir):
    """Create word cloud from document collection."""
    plt.figure(figsize=(12, 8))
    
    # Combine all documents
    text = " ".join(docs)
    
    # Create and generate wordcloud
    wordcloud = WordCloud(width=1200, height=800,
                          background_color='white',
                          min_font_size=10,
                          colormap='viridis',
                          max_words=150).generate(text)
    
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.title(title, fontsize=16)
    plt.tight_layout(pad=0)
    
    # Save wordcloud
    os.makedirs(output_dir, exist_ok=True)
    # Use filename as provided, don't add suffix
    file_path = os.path.join(output_dir, filename)
    plt.savefig(file_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved word cloud to {file_path}")

@log_file_operation
def plot_prompt_distribution(all_prompts, title, filename, output_dir):
    """Plot the distribution of system prompts used in the analysis."""
    if not all_prompts:
        logger.warning("No prompt information to plot")
        return
    
    prompt_counts = {}
    for prompt in all_prompts:
        if prompt in prompt_counts:
            prompt_counts[prompt] += 1
        else:
            prompt_counts[prompt] = 1
    
    # Sort by count
    sorted_prompts = sorted(prompt_counts.items(), key=lambda x: x[1], reverse=True)
    prompts = [p[0] for p in sorted_prompts]
    counts = [p[1] for p in sorted_prompts]
    
    plt.figure(figsize=(12, 8))
    plt.bar(prompts, counts, color='skyblue')
    plt.xlabel('System Prompt')
    plt.ylabel('Frequency')
    plt.title(title)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{filename}_prompt_distribution.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved prompt distribution plot to {file_path}")

@log_file_operation
def plot_topic_modeling(vectorizer, tfidf_matrix, title, filename, output_dir):
    """Perform topic modeling and visualize results."""
    try:
        # Check if we have enough data
        if tfidf_matrix.shape[0] < 3:
            logger.warning("Not enough documents for topic modeling")
            return
            
        # Determine number of topics (between 2 and 5)
        n_topics = min(5, max(2, tfidf_matrix.shape[0] // 2))
        
        # Apply Non-negative Matrix Factorization for topic modeling
        from sklearn.decomposition import NMF
        nmf = NMF(n_components=n_topics, random_state=42)
        nmf_result = nmf.fit_transform(tfidf_matrix)
        
        # Get feature names
        feature_names = vectorizer.get_feature_names_out()
        
        # Create figure
        fig, axes = plt.subplots(n_topics, 1, figsize=(12, n_topics * 3), sharex=True)
        if n_topics == 1:
            axes = [axes]
            
        # Plot top terms for each topic
        for topic_idx, (topic, ax) in enumerate(zip(nmf.components_, axes)):
            top_indices = topic.argsort()[-10:][::-1]  # Top 10 terms
            top_terms = [feature_names[i] for i in top_indices]
            top_weights = topic[top_indices]
            
            ax.barh(top_terms, top_weights, color='skyblue')
            ax.set_title(f'Topic {topic_idx + 1}', fontsize=14)
            ax.set_xlabel('Term Weight', fontsize=12)
            
        plt.suptitle(title, fontsize=16)
        plt.tight_layout()
        
        # Save figure
        os.makedirs(output_dir, exist_ok=True)
        # Use filename as provided
        file_path = os.path.join(output_dir, filename)
        plt.savefig(file_path, dpi=300)
        plt.close()
        
        logger.info(f"Saved topic modeling visualization to {file_path}")
        
    except Exception as e:
        logger.error(f"Error in topic modeling: {e}")
        return None

@log_file_operation
def plot_heatmap(vectorizer, tfidf_matrix, labels, title, filename, output_dir):
    """Create heatmap of term frequencies across documents."""
    # Get feature names
    feature_names = vectorizer.get_feature_names_out()
    
    # Calculate mean TF-IDF for each term
    mean_tfidf = np.array(tfidf_matrix.mean(axis=0)).flatten()
    
    # Get top terms
    top_indices = mean_tfidf.argsort()[-25:]
    top_terms = [feature_names[i] for i in top_indices]
    
    # Extract document-term matrix for top terms
    term_doc_matrix = tfidf_matrix[:, top_indices].toarray()
    
    # Create heatmap
    plt.figure(figsize=(16, 12))
    
    # Create labels for shorter display
    display_labels = [f"{i+1}. {label[:15]}..." if len(label) > 15 else f"{i+1}. {label}" 
                    for i, label in enumerate(labels)]
    
    # Plot heatmap
    sns.heatmap(term_doc_matrix, cmap='viridis', 
               xticklabels=top_terms, yticklabels=display_labels,
               annot=False, cbar_kws={'label': 'TF-IDF Score'})
    
    plt.title(title, fontsize=16)
    plt.xlabel('Top Terms', fontsize=14)
    plt.ylabel('Documents', fontsize=14)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    
    # Save figure
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    # Use filename as provided
    file_path = os.path.join(output_dir, filename)
    plt.savefig(file_path, dpi=300)
    plt.close()
    
    logger.info(f"Saved heatmap to {file_path}")

@log_file_operation
def plot_confidence_intervals(vectorizer, tfidf_matrix, group_labels, title, filename, output_dir):
    """Plot confidence intervals for term frequencies across document groups."""
    try:
        # Get unique groups
        unique_groups = list(set(group_labels))
        if len(unique_groups) < 2:
            logger.warning("Need at least 2 groups for confidence intervals")
            return
            
        # Get feature names
        feature_names = vectorizer.get_feature_names_out()
        
        # Calculate top terms across all documents
        mean_tfidf = np.array(tfidf_matrix.mean(axis=0)).flatten()
        top_indices = mean_tfidf.argsort()[-10:]
        top_terms = [feature_names[i] for i in top_indices]
        
        # Calculate group means and confidence intervals
        group_data = []
        
        for group in unique_groups:
            # Get indices for this group
            group_indices = [i for i, label in enumerate(group_labels) if label == group]
            if not group_indices:
                continue
                
            # Extract group data
            group_matrix = tfidf_matrix[group_indices]
            group_means = np.array(group_matrix.mean(axis=0)).flatten()
            
            # Calculate confidence interval (simplified)
            # Convert sparse matrix to dense array for standard deviation calculation
            if hasattr(group_matrix, 'toarray'):
                # It's a sparse matrix, convert to array for std calculation
                group_matrix_dense = group_matrix.toarray()
                group_std = np.std(group_matrix_dense, axis=0)
            else:
                # It's already a dense array
                group_std = np.array(group_matrix.std(axis=0)).flatten()
                
            n_samples = len(group_indices)
            ci = 1.96 * group_std / np.sqrt(max(1, n_samples))  # 95% confidence interval
            
            # Store data for plotting
            for term_idx in top_indices:
                group_data.append({
                    'Group': group,
                    'Term': feature_names[term_idx],
                    'Mean': group_means[term_idx],
                    'Lower': max(0, group_means[term_idx] - ci[term_idx]),
                    'Upper': group_means[term_idx] + ci[term_idx]
                })
        
        # Convert to DataFrame
        df = pd.DataFrame(group_data)
        
        # Plot
        plt.figure(figsize=(14, 8))
        
        # Set position for bars
        terms = df['Group'].unique()
        x_positions = np.arange(len(terms))
        width = 0.8 / len(unique_groups)
        
        for i, group in enumerate(unique_groups):
            group_df = df[df['Group'] == group]
            
            # Calculate positions for this group
            group_x = [x_positions[list(terms).index(term)] + (i - len(unique_groups)/2 + 0.5) * width 
                      for term in group_df['Group']]
            
            # Plot points and error bars
            plt.errorbar(
                x=group_x,
                y=group_df['Mean'],
                yerr=[group_df['Lower'], group_df['Upper'] - group_df['Mean']],
                fmt='o',
                capsize=5,
                label=group
            )
        
        plt.xticks(x_positions, terms, rotation=45, ha='right')
        plt.xlabel('Terms')
        plt.ylabel('TF-IDF Score')
        plt.title(title)
        plt.legend()
        plt.tight_layout()
        
        # Save
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved confidence interval plot to {output_path}")
        
    except Exception as e:
        logger.error(f"Error plotting confidence intervals: {e}")

@log_file_operation
def plot_system_prompt_comparison(vectorizer, tfidf_matrix, prompt_labels, title, filename, output_dir):
    """Compare term usage across different system prompts."""
    try:
        # Get unique prompt types
        unique_prompts = list(set(prompt_labels))
        
        # Get feature names
        feature_names = vectorizer.get_feature_names_out()
        
        # Calculate top discriminative terms for each prompt
        prompt_terms = []
        
        for prompt in unique_prompts:
            # Get indices for this prompt
            prompt_indices = [i for i, label in enumerate(prompt_labels) if label == prompt]
            if not prompt_indices:
                continue
                
            # Calculate mean for this prompt
            prompt_matrix = tfidf_matrix[prompt_indices]
            prompt_mean = np.array(prompt_matrix.mean(axis=0)).flatten()
            
            # Calculate other prompts mean
            other_indices = [i for i, label in enumerate(prompt_labels) if label != prompt]
            if not other_indices:
                continue
                
            other_matrix = tfidf_matrix[other_indices]
            other_mean = np.array(other_matrix.mean(axis=0)).flatten()
            
            # Calculate difference
            diff = prompt_mean - other_mean
            
            # Get top discriminative terms
            top_diff_indices = diff.argsort()[-5:]
            
            for idx in top_diff_indices:
                prompt_terms.append({
                    'Prompt': prompt,
                    'Term': feature_names[idx],
                    'Difference': diff[idx]
                })
        
        # Convert to DataFrame
        df = pd.DataFrame(prompt_terms)
        
        # Plot
        plt.figure(figsize=(14, 10))
        
        # Plot separate facets for each prompt
        for i, prompt in enumerate(unique_prompts):
            prompt_df = df[df['Prompt'] == prompt].sort_values('Difference', ascending=True)
            
            plt.subplot(len(unique_prompts), 1, i+1)
            plt.barh(prompt_df['Term'], prompt_df['Difference'])
            plt.title(f"Distinctive Terms for {prompt}")
            plt.xlabel("Difference in TF-IDF Score")
            
        plt.suptitle(title)
        plt.tight_layout()
        
        # Save
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved system prompt comparison to {output_path}")
        
    except Exception as e:
        logger.error(f"Error comparing system prompts: {e}")

@log_file_operation
def plot_term_frequency_distribution(tfidf_matrix, vectorizer, title, filename, output_dir):
    """Plot distribution of term frequencies."""
    try:
        # Get feature names and sums
        feature_names = vectorizer.get_feature_names_out()
        term_sums = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
        
        # Get top terms
        top_indices = term_sums.argsort()[-20:]
        top_terms = [feature_names[i] for i in top_indices]
        top_values = term_sums[top_indices]
        
        # Sort for better visualization
        sorted_indices = np.argsort(top_values)
        sorted_terms = [top_terms[i] for i in sorted_indices]
        sorted_values = [top_values[i] for i in sorted_indices]
        
        # Plot
        plt.figure(figsize=(12, 8))
        plt.barh(sorted_terms, sorted_values)
        plt.title(title)
        plt.xlabel("Cumulative TF-IDF Score")
        plt.ylabel("Terms")
        plt.tight_layout()
        
        # Save
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved term frequency distribution to {output_path}")
        
    except Exception as e:
        logger.error(f"Error plotting term frequency distribution: {e}")

@log_file_operation
def plot_term_network(vectorizer, tfidf_matrix, title, filename, output_dir):
    """Create a network visualization of term co-occurrence."""
    try:
        # Get feature names
        feature_names = vectorizer.get_feature_names_out()
        
        # Convert to binary occurrence matrix
        binary_matrix = (tfidf_matrix > 0).astype(int)
        
        # Calculate term co-occurrence
        term_term = binary_matrix.T.dot(binary_matrix)
        
        # Select top terms
        diagonal = term_term.diagonal()
        top_indices = diagonal.argsort()[-30:]
        
        # Extract submatrix for top terms
        sub_matrix = term_term[top_indices][:, top_indices].toarray()
        np.fill_diagonal(sub_matrix, 0)  # Remove self-connections
        
        # Create network
        G = nx.Graph()
        
        # Add nodes
        for i, idx in enumerate(top_indices):
            G.add_node(feature_names[idx], weight=diagonal[idx])
        
        # Add edges
        for i, idx1 in enumerate(top_indices):
            for j, idx2 in enumerate(top_indices):
                if i < j and sub_matrix[i, j] > 0:
                    G.add_edge(feature_names[idx1], feature_names[idx2], weight=sub_matrix[i, j])
        
        # Plot
        plt.figure(figsize=(14, 14))
        
        # Calculate node sizes based on frequency
        node_sizes = [G.nodes[node]['weight'] * 100 for node in G.nodes()]
        
        # Calculate edge widths based on co-occurrence
        edge_widths = [G.edges[edge]['weight'] / 2 for edge in G.edges()]
        
        # Calculate positions using spring layout
        pos = nx.spring_layout(G, k=0.3, iterations=50)
        
        # Draw
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='skyblue', alpha=0.8)
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.5, edge_color='gray')
        nx.draw_networkx_labels(G, pos, font_size=10)
        
        plt.title(title)
        plt.axis('off')
        
        # Save
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved term network to {output_path}")
        
    except Exception as e:
        logger.error(f"Error plotting term network: {e}")

def extract_prompt_info(filename):
    """Extract region ID, prompt type, and date from filename."""
    pattern = r"(.*?)_(.*?)_report_(\d{8})"
    match = re.search(pattern, filename)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return "", "", ""

@log_file_operation
def plot_pca_scree(pca, output_dir):
    """Plot the scree plot (eigenvalues) from PCA."""
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(range(1, len(pca.explained_variance_ratio_) + 1), 
                pca.explained_variance_ratio_, 'o-')
        plt.title('PCA Scree Plot')
        plt.xlabel('Principal Component')
        plt.ylabel('Proportion of Variance Explained')
        plt.xticks(range(1, len(pca.explained_variance_ratio_) + 1))
        plt.grid(True)
        
        # Save
        output_path = os.path.join(output_dir, "pca_scree_plot.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved PCA scree plot to {output_path}")
        
    except Exception as e:
        logger.error(f"Error plotting PCA scree plot: {e}")

@log_file_operation
def plot_pca_cumulative_variance(pca, output_dir):
    """Plot cumulative explained variance ratio from PCA."""
    try:
        cumulative = np.cumsum(pca.explained_variance_ratio_)
        
        plt.figure(figsize=(10, 6))
        plt.plot(range(1, len(cumulative) + 1), cumulative, 'o-')
        plt.axhline(y=0.8, color='r', linestyle='--', label='80% Threshold')
        plt.title('PCA Cumulative Explained Variance')
        plt.xlabel('Number of Components')
        plt.ylabel('Cumulative Explained Variance')
        plt.xticks(range(1, len(cumulative) + 1))
        plt.legend()
        plt.grid(True)
        
        # Save
        output_path = os.path.join(output_dir, "pca_cumulative_variance.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved PCA cumulative variance plot to {output_path}")
        
    except Exception as e:
        logger.error(f"Error plotting PCA cumulative variance: {e}")

@log_file_operation
def plot_pca_loadings_heatmap(pca, vectorizer, output_dir):
    """Create a heatmap of PCA feature loadings."""
    try:
        feature_names = vectorizer.get_feature_names_out()
        
        # Select top components
        n_components = min(5, len(pca.components_))
        
        # For each component, get top features
        top_features = []
        for i in range(n_components):
            # Get top positive and negative loadings
            indices = np.argsort(np.abs(pca.components_[i]))[-15:]
            top_features.extend(indices)
        
        # Remove duplicates while preserving order
        unique_features = []
        for feature in top_features:
            if feature not in unique_features:
                unique_features.append(feature)
        
        # Limit to top 30 features
        unique_features = unique_features[:30]
        
        # Create loadings matrix
        loadings = pca.components_[:n_components, unique_features].T
        
        # Create labels
        feature_labels = [feature_names[i] for i in unique_features]
        
        # Create heatmap
        plt.figure(figsize=(12, 8))
        sns.heatmap(loadings, annot=True, cmap='coolwarm', center=0,
                  yticklabels=feature_labels,
                  xticklabels=[f"PC{i+1}" for i in range(n_components)])
        plt.title("PCA Loadings Heatmap for Top Features")
        plt.tight_layout()
        
        # Save
        output_path = os.path.join(output_dir, "pca_loadings_heatmap.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved PCA loadings heatmap to {output_path}")
        
    except Exception as e:
        logger.error(f"Error plotting PCA loadings heatmap: {e}")

@log_file_operation
def save_pca_top_features(pca, vectorizer, output_dir):
    """Save the top features for each PCA component to a CSV file."""
    try:
        feature_names = vectorizer.get_feature_names_out()
        
        # Create output file
        output_path = os.path.join(output_dir, "pca_top_features.txt")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Top Features by PCA Component\n\n")
            
            for i, component in enumerate(pca.components_):
                # Get top positive features
                pos_indices = component.argsort()[::-1][:10]
                pos_features = [(feature_names[idx], component[idx]) for idx in pos_indices]
                
                # Get top negative features
                neg_indices = component.argsort()[:10]
                neg_features = [(feature_names[idx], component[idx]) for idx in neg_indices]
                
                # Write to file
                f.write(f"## Component {i+1}\n")
                f.write(f"### Explained variance: {pca.explained_variance_ratio_[i]:.4f}\n\n")
                
                f.write("#### Top Positive Features\n")
                for feature, weight in pos_features:
                    f.write(f"- {feature}: {weight:.4f}\n")
                
                f.write("\n#### Top Negative Features\n")
                for feature, weight in neg_features:
                    f.write(f"- {feature}: {weight:.4f}\n")
                
                f.write("\n---\n\n")
                
        logger.info(f"Saved PCA top features to {output_path}")
        
    except Exception as e:
        logger.error(f"Error saving PCA top features: {e}")

@log_file_operation
def plot_pca_3d(pca_result, color_labels, output_dir):
    """Create a 3D scatter plot of the first three PCA components."""
    try:
        if pca_result.shape[1] < 3:
            logger.warning("Need at least 3 components for 3D PCA plot")
            return
            
        # Create dataframe
        df = pd.DataFrame({
            'PC1': pca_result[:, 0],
            'PC2': pca_result[:, 1],
            'PC3': pca_result[:, 2],
            'label': color_labels
        })
        
        # Create 3D plot
        fig = px.scatter_3d(df, x='PC1', y='PC2', z='PC3', color='label',
                          title='3D PCA Plot',
                          labels={'PC1': 'PC1', 'PC2': 'PC2', 'PC3': 'PC3'})
        
        # Update marker size
        fig.update_traces(marker=dict(size=5))
        
        # Save
        output_path = os.path.join(output_dir, "pca_3d.html")
        fig.write_html(output_path)
        logger.info(f"Saved 3D PCA plot to {output_path}")
        
    except Exception as e:
        logger.error(f"Error creating 3D PCA plot: {e}") 