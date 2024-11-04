import os
import sys
import logging
import argparse
from typing import List, Tuple, Dict
import numpy as np
import spacy
from pathlib import Path
import re

from Visualization_Methods import (
    read_markdown_files, preprocess_text, perform_tfidf_and_dim_reduction,
    plot_dimension_reduction, plot_word_importance, plot_pca_eigen_terms,
    create_word_cloud, plot_prompt_distribution, plot_topic_modeling,
    plot_heatmap, plot_confidence_intervals, plot_system_prompt_comparison,
    plot_term_frequency_distribution, plot_term_network,
    extract_prompt_info, plot_pca_scree, plot_pca_cumulative_variance,
    plot_pca_loadings_heatmap, save_pca_top_features, plot_pca_3d
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_regional_files(base_dir: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Collect all research files from regional subdirectories.
    
    Returns:
        Dict with structure:
        {
            'region_name': {
                'research_reports': [...],
                'business_cases': [...]
            }
        }
    """
    regional_files = {}
    
    try:
        # Iterate through all subdirectories in Outputs/
        for region_dir in Path(base_dir).glob("*"):
            if region_dir.is_dir():
                region_name = region_dir.name
                regional_files[region_name] = {
                    'research_reports': [],
                    'business_cases': []
                }
                
                # Collect all markdown files
                for md_file in region_dir.glob("*.md"):
                    file_path = str(md_file)
                    if 'business_case' in file_path:
                        regional_files[region_name]['business_cases'].append(file_path)
                    elif 'report' in file_path:
                        regional_files[region_name]['research_reports'].append(file_path)
        
        logger.info(f"Found {len(regional_files)} regions with research data")
        return regional_files
    
    except Exception as e:
        logger.error(f"Error collecting regional files: {e}")
        return {}

def extract_region_info(filename: str) -> Tuple[str, str, str]:
    """Extract region ID, type, and date from filename."""
    pattern = r"(CA-[A-Z]{3})_(\w+)_(\d{8})"
    match = re.search(pattern, filename)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return "", "", ""

def analyze_regional_research(regional_files: Dict[str, Dict[str, List[str]]], 
                            output_dir: str,
                            nlp) -> None:
    """Analyze research files for all regions."""
    
    # Prepare data structures for analysis
    all_documents = []
    all_filenames = []
    region_labels = []
    document_types = []
    
    # Collect all documents
    for region, file_types in regional_files.items():
        for doc_type, files in file_types.items():
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        all_documents.append(content)
                        all_filenames.append(os.path.basename(file_path))
                        region_labels.append(region)
                        document_types.append(doc_type)
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
    
    if not all_documents:
        logger.warning("No documents found for analysis")
        return
    
    logger.info(f"Processing {len(all_documents)} documents from {len(regional_files)} regions")
    
    # Preprocess documents
    preprocessed_docs = [preprocess_text(doc, nlp) for doc in all_documents]
    
    # Create visualization subfolders
    vis_dir = Path(output_dir)
    vis_dir.mkdir(exist_ok=True)
    for subdir in ['regional', 'comparative', 'topic_analysis', 'network_analysis']:
        (vis_dir / subdir).mkdir(exist_ok=True)
    
    # Perform analyses
    try:
        # 1. Dimension Reduction Analysis
        pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne = perform_tfidf_and_dim_reduction(
            preprocessed_docs,
            n_components=min(30, len(all_documents) - 1)
        )
        
        # Plot by region
        plot_dimension_reduction(pca_result, all_filenames, region_labels,
                               "Regional Research PCA", "regional_pca.png",
                               "PCA", vectorizer, pca, vis_dir / 'regional')
        
        # Plot by document type
        plot_dimension_reduction(pca_result, all_filenames, document_types,
                               "Document Type PCA", "document_type_pca.png",
                               "PCA", vectorizer, pca, vis_dir / 'regional')
        
        # 2. Topic Analysis
        tfidf_matrix = vectorizer.fit_transform(preprocessed_docs)
        plot_topic_modeling(vectorizer, tfidf_matrix, 
                          "Regional Research Topics", "regional_topics.png",
                          vis_dir / 'topic_analysis')
        
        # 3. Regional Comparisons
        plot_heatmap(vectorizer, tfidf_matrix, all_filenames,
                    "Inter-regional Term Usage", "regional_term_heatmap.png",
                    vis_dir / 'comparative')
        
        # 4. Network Analysis
        plot_term_network(vectorizer, tfidf_matrix,
                         "Regional Research Term Network", "term_network.png",
                         vis_dir / 'network_analysis')
        
        # 5. Regional Word Clouds
        for region in regional_files.keys():
            region_docs = [doc for doc, reg in zip(preprocessed_docs, region_labels) if reg == region]
            if region_docs:
                create_word_cloud(region_docs,
                                f"{region} Key Terms", f"{region}_wordcloud.png",
                                vis_dir / 'regional')
        
        # 6. Comparative Analysis
        plot_confidence_intervals(vectorizer, tfidf_matrix, region_labels,
                                "Regional Term Usage Confidence Intervals", 
                                "regional_confidence_intervals.png",
                                vis_dir / 'comparative')
        
        # 7. Enhanced PCA Visualizations
        if pca_result is not None:
            plot_pca_scree(pca, vis_dir / 'comparative')
            plot_pca_cumulative_variance(pca, vis_dir / 'comparative')
            plot_pca_loadings_heatmap(pca, vectorizer, vis_dir / 'comparative')
            save_pca_top_features(pca, vectorizer, vis_dir / 'comparative')
            plot_pca_3d(pca_result, region_labels, vis_dir / 'comparative')
        
        logger.info("Completed all visualizations")
        
    except Exception as e:
        logger.error(f"Error in analysis: {e}")

def main(input_folder: str, output_folder: str) -> None:
    """Main function to orchestrate regional research analysis."""
    logger.info(f"Starting analysis of regional research in: {input_folder}")
    
    # Verify input folder exists
    if not os.path.isdir(input_folder):
        logger.error(f"Input directory not found: {input_folder}")
        return
    
    # Load spaCy model
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        logger.error(f"Failed to load spaCy model: {str(e)}")
        sys.exit(1)
    
    # Collect regional files
    regional_files = collect_regional_files(input_folder)
    if not regional_files:
        logger.error("No regional research files found")
        return
    
    # Create output directory
    os.makedirs(output_folder, exist_ok=True)
    
    # Perform analysis
    analyze_regional_research(regional_files, output_folder, nlp)
    
    logger.info(f"Analysis complete. Results saved in: {output_folder}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze regional research outputs.")
    parser.add_argument("--input", default="Outputs",
                       help="Path to the Outputs directory containing regional research")
    parser.add_argument("--output", default="Visualizations",
                       help="Path to save visualization outputs")
    args = parser.parse_args()
    
    # Get absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, args.input)
    output_dir = os.path.join(script_dir, args.output)
    
    main(input_dir, output_dir)
