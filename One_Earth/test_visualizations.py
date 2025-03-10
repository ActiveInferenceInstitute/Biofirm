#!/usr/bin/env python3
"""
Test script for visualizations in Visualization_Methods.py.
This script tests every visualization function to ensure they're being properly output and logged.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import all visualization methods
try:
    from Visualization_Methods import (
        read_markdown_files, preprocess_text, perform_tfidf_and_dim_reduction,
        plot_dimension_reduction, plot_word_importance, plot_pca_eigen_terms,
        create_word_cloud, plot_prompt_distribution, plot_topic_modeling,
        plot_heatmap, plot_confidence_intervals, plot_system_prompt_comparison,
        plot_term_frequency_distribution, plot_term_network,
        extract_prompt_info, plot_pca_scree, plot_pca_cumulative_variance,
        plot_pca_loadings_heatmap, save_pca_top_features, plot_pca_3d,
        WORDCLOUD_AVAILABLE, NETWORKX_AVAILABLE, PLOTLY_AVAILABLE, SKLEARN_AVAILABLE
    )
    logger.info("Successfully imported visualization methods")
except ImportError as e:
    logger.error(f"Failed to import visualization methods: {e}")
    raise

def create_test_documents():
    """Create some test documents for visualization."""
    docs = [
        "This is a test document about bioregions and ecosystems. It contains words related to sustainability.",
        "Climate change affects ecosystems across different bioregions. Biodiversity is crucial for ecosystem health.",
        "Sustainable development requires understanding the unique characteristics of each bioregion.",
        "Water resources vary across bioregions, affecting agricultural practices and biodiversity.",
        "Forests in temperate bioregions differ significantly from those in tropical regions.",
        "Conservation efforts should be tailored to the specific needs of each bioregion.",
        "Human activities can disrupt the natural balance of ecosystems within bioregions.",
        "Biodiversity hotspots represent areas with exceptionally high species diversity.",
        "Restoration ecology focuses on reviving damaged ecosystems within various bioregions.",
        "Climate resilience strategies must account for bioregional differences."
    ]
    return docs

def test_all_visualizations():
    """Test all visualization functions."""
    # Create output directory
    output_dir = "Visualizations/test_vis"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    
    # Create test documents
    docs = create_test_documents()
    logger.info(f"Created {len(docs)} test documents")
    
    # Preprocess documents
    preprocessed_docs = [preprocess_text(doc, None) for doc in docs]
    logger.info("Preprocessed test documents")
    
    # Perform TF-IDF and dimension reduction
    if SKLEARN_AVAILABLE:
        logger.info("Testing TF-IDF and dimension reduction")
        try:
            pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne = perform_tfidf_and_dim_reduction(
                preprocessed_docs, n_components=5, min_df=1, max_df=1.0
            )
            logger.info("Successfully performed TF-IDF and dimension reduction")
            
            # Get TF-IDF matrix directly
            tfidf_matrix = vectorizer.transform(preprocessed_docs)
            
            # Create labels for plots
            labels = [f"Doc {i+1}" for i in range(len(docs))]
            color_labels = ["Group A" if i < 5 else "Group B" for i in range(len(docs))]
            
            # Test plot_dimension_reduction with PCA
            logger.info("Testing plot_dimension_reduction with PCA")
            plot_dimension_reduction(
                pca_result, labels, color_labels, "PCA of Documents", 
                "pca_plot.png", "PCA", vectorizer, pca, output_dir
            )
            
            # Test plot_dimension_reduction with LSA
            logger.info("Testing plot_dimension_reduction with LSA")
            plot_dimension_reduction(
                lsa_result, labels, color_labels, "LSA of Documents", 
                "lsa_plot.png", "LSA", vectorizer, lsa, output_dir
            )
            
            # Test plot_dimension_reduction with t-SNE
            if tsne_result is not None:
                logger.info("Testing plot_dimension_reduction with t-SNE")
                plot_dimension_reduction(
                    tsne_result, labels, color_labels, "t-SNE of Documents", 
                    "tsne_plot.png", "t-SNE", vectorizer, tsne, output_dir
                )
            
            # Test plot_word_importance
            logger.info("Testing plot_word_importance")
            plot_word_importance(
                vectorizer, pca, "PCA", "Top Words by PCA Component", 
                "word_importance", output_dir
            )
            
            # Test plot_pca_eigen_terms
            logger.info("Testing plot_pca_eigen_terms")
            plot_pca_eigen_terms(
                pca, vectorizer, "PCA Eigen Terms", "pca_eigen_terms", output_dir
            )
            
            # Test plot_heatmap
            logger.info("Testing plot_heatmap")
            plot_heatmap(
                vectorizer, tfidf_matrix, labels, "Term Frequency Heatmap", 
                "term_heatmap", output_dir
            )
            
            # Test plot_confidence_intervals
            logger.info("Testing plot_confidence_intervals")
            plot_confidence_intervals(
                vectorizer, tfidf_matrix, color_labels, "Term Confidence Intervals", 
                "confidence_intervals", output_dir
            )
            
            # Test plot_term_frequency_distribution
            logger.info("Testing plot_term_frequency_distribution")
            plot_term_frequency_distribution(
                tfidf_matrix, vectorizer, "Term Frequency Distribution", 
                "term_frequency", output_dir
            )
            
            # Test PCA-specific visualizations
            logger.info("Testing PCA-specific visualizations")
            plot_pca_scree(pca, output_dir)
            plot_pca_cumulative_variance(pca, output_dir)
            plot_pca_loadings_heatmap(pca, vectorizer, output_dir)
            save_pca_top_features(pca, vectorizer, output_dir)
            
            if len(pca_result[0]) >= 3:  # Need at least 3 dimensions for 3D plot
                logger.info("Testing plot_pca_3d")
                plot_pca_3d(pca_result, color_labels, output_dir)
            
        except Exception as e:
            logger.error(f"Error in TF-IDF and visualization tests: {e}")
    else:
        logger.warning("sklearn not available, skipping TF-IDF and related visualizations")
    
    # Test create_word_cloud
    if WORDCLOUD_AVAILABLE:
        logger.info("Testing create_word_cloud")
        try:
            create_word_cloud(
                docs, "Test Word Cloud", "word_cloud", output_dir
            )
        except Exception as e:
            logger.error(f"Error in word cloud test: {e}")
    else:
        logger.warning("wordcloud not available, skipping word cloud test")
    
    # Test plot_term_network
    if NETWORKX_AVAILABLE:
        logger.info("Testing plot_term_network")
        try:
            plot_term_network(
                vectorizer, tfidf_matrix, "Term Network", "term_network", output_dir
            )
        except Exception as e:
            logger.error(f"Error in term network test: {e}")
    else:
        logger.warning("networkx not available, skipping term network test")
    
    # Test plot_topic_modeling
    if SKLEARN_AVAILABLE:
        logger.info("Testing plot_topic_modeling")
        try:
            plot_topic_modeling(
                vectorizer, tfidf_matrix, "Topic Modeling", "topic_modeling", output_dir
            )
        except Exception as e:
            logger.error(f"Error in topic modeling test: {e}")
    
    # Test plot_prompt_distribution
    logger.info("Testing plot_prompt_distribution")
    try:
        all_prompts = {
            "system": ["System prompt 1", "System prompt 2"],
            "user": ["User prompt 1", "User prompt 2", "User prompt 3"],
            "assistant": ["Assistant response 1", "Assistant response 2"]
        }
        plot_prompt_distribution(
            all_prompts, "Prompt Distribution", "prompt_distribution", output_dir
        )
    except Exception as e:
        logger.error(f"Error in prompt distribution test: {e}")
    
    # Test plot_system_prompt_comparison
    if SKLEARN_AVAILABLE:
        logger.info("Testing plot_system_prompt_comparison")
        try:
            prompt_labels = ["Prompt A", "Prompt B", "Prompt C", "Prompt D", "Prompt E",
                            "Prompt A", "Prompt B", "Prompt C", "Prompt D", "Prompt E"]
            plot_system_prompt_comparison(
                vectorizer, tfidf_matrix, prompt_labels, "Prompt Comparison", 
                "prompt_comparison", output_dir
            )
        except Exception as e:
            logger.error(f"Error in system prompt comparison test: {e}")
    
    logger.info("Visualization tests completed")
    return output_dir

if __name__ == "__main__":
    logger.info("Starting visualization tests")
    output_dir = test_all_visualizations()
    logger.info(f"All tests completed. Visualizations saved to {output_dir}") 