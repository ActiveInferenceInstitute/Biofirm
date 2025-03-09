import os
import sys
import logging
import argparse
from typing import List, Tuple, Dict
import numpy as np
import pandas as pd  # Ensure pandas is imported at the top level
# Remove automatic spaCy installation and import
# Use minimal NLP implementation instead
spacy = None  # Set spaCy to None to indicate it's not available
logging.info("Using minimal NLP processing (spaCy not required)")

from pathlib import Path
import re
from run_pipeline import log_file_operation
import glob

# Set up logging first to capture import errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import scikit-learn components with try/except to handle missing dependencies
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import PCA, TruncatedSVD
    from sklearn.manifold import TSNE
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not available. Some visualization features will be limited.")
    SKLEARN_AVAILABLE = False

# Import with try/except to handle missing dependencies
try:
    from Visualization_Methods import (
        read_markdown_files, preprocess_text, perform_tfidf_and_dim_reduction,
        plot_dimension_reduction, plot_word_importance, plot_pca_eigen_terms,
        create_word_cloud, plot_prompt_distribution, plot_topic_modeling,
        plot_heatmap, plot_confidence_intervals, plot_system_prompt_comparison,
        plot_term_frequency_distribution, plot_term_network,
        extract_prompt_info, plot_pca_scree, plot_pca_cumulative_variance,
        plot_pca_loadings_heatmap, save_pca_top_features, plot_pca_3d,
        WORDCLOUD_AVAILABLE, NETWORKX_AVAILABLE, PLOTLY_AVAILABLE
    )
    VISUALIZATION_METHODS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Error importing visualization methods: {str(e)}")
    VISUALIZATION_METHODS_AVAILABLE = False
    # Define constants as False if import fails
    WORDCLOUD_AVAILABLE = False
    NETWORKX_AVAILABLE = False
    PLOTLY_AVAILABLE = False

def collect_regional_files(base_dir: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Collect all relevant markdown files from the output directory.
    
    Args:
        base_dir: Base directory containing regional subdirectories.
        
    Returns:
        Dictionary mapping region names to dictionaries of document types and their file paths.
    """
    regional_files = {}
    
    try:
        # Use the base_dir directly instead of looking for an "Outputs" subdirectory
        outputs_dir = base_dir
        if not os.path.exists(outputs_dir):
            logger.warning(f"Outputs directory not found: {outputs_dir}")
            # Create an empty directory structure and return it
            return {}
        
        # Map to keep track of regions that have been processed already
        # This helps when there are two directories for the same region (with spaces and with underscores)
        processed_regions = {}
        
        # Iterate through region directories
        for region_dir in os.listdir(outputs_dir):
            region_path = os.path.join(outputs_dir, region_dir)
            
            # Skip if not a directory
            if not os.path.isdir(region_path):
                continue
                
            # Extract the base region name (without format differences)
            # This will help us identify the same region with different formats
            base_region_name = region_dir.replace('_', ' ').strip()
            
            # Initialize data structures for this region if not already done
            if base_region_name not in regional_files:
                regional_files[base_region_name] = {
                    'research': [],
                    'business_case': [],
                    'other': []
                }
            
            # Find all markdown files in the region directory
            for root, _, files in os.walk(region_path):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        
                        # Determine document type based on filename
                        doc_type = 'other'  # Default
                        if 'research' in file.lower() or 'consolidated_research_' in file.lower():
                            doc_type = 'research'
                        elif 'business' in file.lower() or 'case' in file.lower():
                            doc_type = 'business_case'
                            
                        # Add file to appropriate list
                        regional_files[base_region_name][doc_type].append(file_path)
            
            # Mark this region as processed
            processed_regions[base_region_name] = True
        
        # Remove regions with no markdown files
        empty_regions = [region for region, files in regional_files.items() 
                        if not any(files.values())]
        for region in empty_regions:
            del regional_files[region]
        
        # Check if we found any markdown files
        if not regional_files:
            logger.warning("No markdown files found in any region directories!")
        else:
            research_regions = [region for region, files in regional_files.items() 
                              if files['research']]
            logger.info(f"Found {len(research_regions)} regions with research files")
            
        return regional_files
    except Exception as e:
        logger.error(f"Error collecting regional files: {str(e)}")
        return {}

def extract_file_metadata(filename: str) -> Tuple[str, str, str]:
    """
    Extract metadata from filename.
    
    Args:
        filename: Name of the file to extract metadata from.
        
    Returns:
        Tuple of (region_id, report_type, date)
    """
    parts = filename.split('_')
    
    # Default values
    region_id = 'unknown'
    report_type = 'unknown'
    date = 'unknown'
    
    # Extract region_id if available
    if len(parts) > 1:
        region_id = parts[1]
    
    # Extract report type if available
    if 'research' in filename:
        report_type = 'research'
    elif 'business' in filename:
        report_type = 'business_case'
    
    # Extract date if available (assuming date is in format YYYYMMDD)
    date_pattern = r'\d{8}'
    date_match = re.search(date_pattern, filename)
    if date_match:
        date = date_match.group(0)
    
    return region_id, report_type, date

def analyze_research_data(outputs_root="Outputs", visualizations_root="Visualizations"):
    """
    Analyze research data and create visualizations.
    
    Args:
        outputs_root: Root directory containing outputs from research phase.
        visualizations_root: Directory to save visualizations.
    """
    # Initialize directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outputs_dir = os.path.join(script_dir, outputs_root)
    output_dir = os.path.join(script_dir, visualizations_root)
    
    # Create visualization directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if the Outputs directory exists
    if not os.path.exists(outputs_dir):
        logger.error(f"Outputs directory not found: {outputs_dir}")
        return
    
    # Create a mapping of raw region names to normalized region names
    region_dirs = [d for d in os.listdir(outputs_dir) 
                  if os.path.isdir(os.path.join(outputs_dir, d))]
    
    if not region_dirs:
        logger.warning("No region directories found in Outputs folder")
        return
    
    # Normalize region names for consistent processing
    normalized_regions = {}
    region_to_normalized = {}
    
    # First pass: create a mapping from raw directory names to normalized names
    for region_dir_name in region_dirs:
        # Extract the base name by removing both underscores and spaces
        base_name = region_dir_name.replace('_', ' ')
        # Create a consistent normalized key
        normalized_key = base_name.replace(' ', '_').replace('/', '_')
        
        # Store the mapping from raw directory name to normalized key
        region_to_normalized[region_dir_name] = normalized_key
        
        # Initialize the list of directories for this normalized key if it doesn't exist
        if normalized_key not in normalized_regions:
            normalized_regions[normalized_key] = []
        
        # Add this directory to the list for this normalized key
        normalized_regions[normalized_key].append(region_dir_name)
    
    # Second pass: for each normalized key, choose the best directory to use
    final_regions = {}
    for normalized_key, dir_list in normalized_regions.items():
        if len(dir_list) == 1:
            # If there's only one directory, use it
            final_regions[normalized_key] = dir_list[0]
        else:
            # If there are multiple directories, prefer the one with underscores
            # as it's more likely to be the newer format
            underscored_dirs = [d for d in dir_list if '_' in d]
            if underscored_dirs:
                final_regions[normalized_key] = underscored_dirs[0]
            else:
                # If none have underscores, just use the first one
                final_regions[normalized_key] = dir_list[0]
    
    # Replace normalized_regions with our final mapping
    normalized_regions = final_regions
    
    # Load spaCy model for text processing
    try:
        nlp = load_spacy_model()
    except Exception as e:
        logger.error(f"Error loading spaCy model: {str(e)}")
        return
    
    # Collect files by region and type
    regional_files = {}
    
    # Check each region directory
    for normalized_name, region_dir_name in normalized_regions.items():
        region_path = os.path.join(outputs_dir, region_dir_name)
        
        # Check for research reports
        research_reports = glob.glob(os.path.join(region_path, "research_*.txt"))
        
        # Also check for consolidated research JSON files
        consolidated_research = glob.glob(os.path.join(region_path, "*_consolidated_research_*.json"))
        research_reports.extend(consolidated_research)
        
        # Skip regions without research reports
        if not research_reports:
            logger.warning(f"No research reports found for region: {normalized_name}")
            continue
        
        # Check for business case document
        business_case = glob.glob(os.path.join(region_path, "business_case_*.txt"))
        
        # Initialize dictionary for region
        regional_files[normalized_name] = {
            "research": research_reports,
            "business_case": business_case
        }
    
    # Analyze data if we have regions with files
    if regional_files:
        process_regional_data(regional_files, output_dir, nlp)
        logger.info("Visualization and analysis complete.")
    else:
        logger.error("No regions with sufficient research data found. Visualization skipped.")
        
    return

def main(input_folder: str, output_folder: str) -> None:
    """Main function to orchestrate regional research analysis."""
    logger.info(f"Starting analysis of regional research in: {input_folder}")
    
    # Verify input folder exists
    if not os.path.isdir(input_folder):
        logger.error(f"Input directory not found: {input_folder}")
        return
    
    # Check if visualization methods are available
    if not VISUALIZATION_METHODS_AVAILABLE:
        logger.error("Visualization methods not available. Cannot continue analysis.")
        return
    
    # Use the new normalized analysis function 
    try:
        analyze_research_data(outputs_root=input_folder, visualizations_root=output_folder)
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        
        # Create minimal output to avoid downstream errors
        try:
            # Create empty summary file
            empty_summary = pd.DataFrame({
                'document_type': [],
                'region': [],
                'filename': [],
                'content_length': [],
                'word_count': []
            })
            summary_path = os.path.join(output_folder, 'document_summary.csv')
            os.makedirs(os.path.dirname(summary_path), exist_ok=True)
            empty_summary.to_csv(summary_path, index=False)
            logger.info(f"Created empty summary file at {summary_path}")
            
            # Create empty directories for visualizations
            os.makedirs(os.path.join(output_folder, 'general'), exist_ok=True)
            os.makedirs(os.path.join(output_folder, 'regions'), exist_ok=True)
            os.makedirs(os.path.join(output_folder, 'comparisons'), exist_ok=True)
            logger.info("Created visualization directories")
        except Exception as fallback_error:
            logger.error(f"Failed to create fallback outputs: {str(fallback_error)}")

def load_spacy_model():
    """
    Load the spaCy language model or create a minimal replacement.
    
    Returns:
        A spaCy language model or a minimal replacement.
    """
    try:
        if spacy is not None:
            try:
                nlp = spacy.load("en_core_web_sm")
                logger.info("Successfully loaded spaCy model")
                return nlp
            except OSError:
                logger.warning("spaCy model not found. Using basic text processing instead.")
                return create_minimal_nlp()
        else:
            logger.warning("spaCy not available. Using basic text processing instead.")
            return create_minimal_nlp()
    except Exception as e:
        logger.error(f"Failed to set up NLP processing: {str(e)}")
        logger.warning("Will continue with limited functionality")
        return create_minimal_nlp()

def create_minimal_nlp():
    """Create a minimal replacement for spaCy NLP model."""
    class MinimalDoc:
        def __init__(self, text):
            self.text = text
            self.words = text.split()
        
        def __iter__(self):
            for word in self.words:
                yield word
    
    class MinimalNLP:
        def __call__(self, text):
            return MinimalDoc(text)
    
    return MinimalNLP()

def preprocess_text(text: str, nlp) -> str:
    """
    Preprocess text for analysis.
    
    Args:
        text: Text to preprocess.
        nlp: spaCy language model.
        
    Returns:
        Preprocessed text.
    """
    # Basic preprocessing
    text = text.lower()
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove special characters and numbers
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    
    # If we have spaCy, use it for advanced processing
    if hasattr(nlp, 'pipe') and callable(getattr(nlp, 'pipe', None)):
        # Use spaCy for advanced processing
        doc = nlp(text)
        # Remove stopwords and lemmatize
        processed = ' '.join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct and len(token.text.strip()) > 1])
    else:
        # Simple stopword filtering without spaCy
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
        
        words = text.split()
        processed = ' '.join([word for word in words if word not in stopwords and len(word.strip()) > 1])
    
    return processed

def process_regional_data(regional_files, output_dir, nlp):
    """
    Process regional data and create visualizations.
    
    Args:
        regional_files: Dictionary mapping normalized region names to document types and file paths.
        output_dir: Directory to save visualizations.
        nlp: spaCy language model for text processing.
    """
    # Create output directories
    os.makedirs(os.path.join(output_dir, "general"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "regions"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "comparisons"), exist_ok=True)
    
    # Access global dependency flags
    global VISUALIZATION_METHODS_AVAILABLE, WORDCLOUD_AVAILABLE, NETWORKX_AVAILABLE, SKLEARN_AVAILABLE
    
    # Collect all documents for analysis
    all_docs = []
    all_filenames = []
    all_regions = []
    all_doc_types = []
    
    region_count = 0
    doc_count = 0
    
    # Process each region
    for region, file_types in regional_files.items():
        region_count += 1
        region_docs = []
        region_filenames = []
        region_doc_types = []
        
        # Process each document type
        for doc_type, files in file_types.items():
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # Handle JSON files differently
                        if file_path.endswith('.json'):
                            import json
                            try:
                                data = json.load(f)
                                # Extract the content from the JSON structure
                                # First try to find content in common JSON structures
                                if isinstance(data, dict):
                                    # Try different possible content fields
                                    for field in ['content', 'text', 'research', 'body']:
                                        if field in data:
                                            text = data[field]
                                            break
                                    else:
                                        # If no specific field found, use the whole JSON
                                        text = json.dumps(data)
                                else:
                                    # If not a dict, convert the whole JSON to text
                                    text = json.dumps(data)
                            except json.JSONDecodeError:
                                # If JSON is invalid, just read it as text
                                f.seek(0)  # Go back to start of file
                                text = f.read()
                        else:
                            # Regular text file
                            text = f.read()
                    
                    # Add to region-specific lists
                    region_docs.append(text)
                    region_filenames.append(os.path.basename(file_path))
                    region_doc_types.append(doc_type)
                    
                    # Add to all documents lists
                    all_docs.append(text)
                    all_filenames.append(os.path.basename(file_path))
                    all_regions.append(region)
                    all_doc_types.append(doc_type)
                    
                    doc_count += 1
                    
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
        
        # Skip regions with insufficient documents
        if len(region_docs) < 1:
            logger.warning(f"Insufficient documents for region {region}, skipping region-specific analysis")
            continue
            
        # Apply region-specific preprocessing and analysis if we have enough documents
        try:
            logger.info(f"Processing region {region} with {len(region_docs)} documents")
            
            # Preprocess text
            preprocessed_docs = [preprocess_text(doc, nlp) for doc in region_docs]
            
            # Create region output directory
            region_dir = os.path.join(output_dir, "regions", region)
            os.makedirs(region_dir, exist_ok=True)
            
            # Skip TF-IDF if only one document or sklearn is not available
            if len(preprocessed_docs) >= 2 and VISUALIZATION_METHODS_AVAILABLE and SKLEARN_AVAILABLE:
                try:
                    # Perform TF-IDF and dimension reduction
                    try:
                        results = perform_tfidf_and_dim_reduction(
                            preprocessed_docs, n_components=min(2, len(preprocessed_docs)))
                        
                        if results:
                            pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne = results
                            
                            # Extract TF-IDF matrix from vectorizer
                            tfidf_matrix = vectorizer.transform(preprocessed_docs)
                            
                            # Generate visualizations
                            if pca_result is not None and pca is not None:
                                plot_dimension_reduction(
                                    pca_result, region_filenames, region_doc_types,
                                    f"PCA of {region} Documents", "pca_plot.png", "PCA",
                                    vectorizer, pca, region_dir
                                )
                            
                            if tsne_result is not None and tsne is not None:
                                plot_dimension_reduction(
                                    tsne_result, region_filenames, region_doc_types,
                                    f"t-SNE of {region} Documents", "tsne_plot.png", "t-SNE",
                                    vectorizer, tsne, region_dir
                                )
                            
                            # Use pca for word importance since it has components_
                            if pca and hasattr(pca, 'components_'):
                                plot_word_importance(
                                    vectorizer, pca, "PCA",
                                    f"Important Terms in {region}", "important_terms", region_dir
                                )
                            
                            plot_heatmap(
                                vectorizer, tfidf_matrix, region_filenames,
                                f"Document-Term Heatmap for {region}", "term_heatmap.png", region_dir
                            )
                        else:
                            logger.warning(f"Dimension reduction returned no results for region {region}")
                    except Exception as e:
                        logger.error(f"Error performing dimension reduction for region {region}: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Error during visualization for region {region}: {str(e)}")
                    
            # Create word cloud if available
            if WORDCLOUD_AVAILABLE and VISUALIZATION_METHODS_AVAILABLE:
                try:
                    create_word_cloud(
                        preprocessed_docs, f"Word Cloud for {region}",
                        "word_cloud.png", region_dir
                    )
                except Exception as e:
                    logger.error(f"Error creating word cloud for region {region}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during analysis for region {region}: {str(e)}")
    
    # Skip overall analysis if insufficient documents
    if doc_count < 1:
        logger.warning("No documents found for analysis")
        return
        
    # Create document summary
    create_documents_summary(all_docs, all_filenames, all_regions, all_doc_types, output_dir)
    
    # Perform overall analysis if we have multiple documents
    if doc_count >= 2 and VISUALIZATION_METHODS_AVAILABLE and SKLEARN_AVAILABLE:
        try:
            logger.info(f"Performing overall analysis across {region_count} regions with {doc_count} total documents")
            
            # Preprocess all documents
            all_preprocessed = [preprocess_text(doc, nlp) for doc in all_docs]
            
            # Perform TF-IDF and dimension reduction
            try:
                results = perform_tfidf_and_dim_reduction(
                    all_preprocessed, n_components=min(2, len(all_preprocessed)))
                
                if results and len(results) >= 7:
                    pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne = results
                    
                    # Get the TF-IDF matrix from the vectorizer
                    tfidf_matrix = vectorizer.transform(all_preprocessed)
                    
                    # Create general visualizations
                    general_dir = os.path.join(output_dir, "general")
                    
                    plot_dimension_reduction(
                        pca_result, all_filenames, all_regions,
                        "PCA of All Documents by Region", "pca_by_region.png", "PCA",
                        vectorizer, pca, general_dir
                    )
                    
                    plot_dimension_reduction(
                        pca_result, all_filenames, all_doc_types,
                        "PCA of All Documents by Type", "pca_by_type.png", "PCA",
                        vectorizer, pca, general_dir
                    )
                    
                    plot_dimension_reduction(
                        tsne_result, all_filenames, all_regions,
                        "t-SNE of All Documents by Region", "tsne_by_region.png", "t-SNE",
                        vectorizer, tsne, general_dir
                    )
                    
                    plot_dimension_reduction(
                        tsne_result, all_filenames, all_doc_types,
                        "t-SNE of All Documents by Type", "tsne_by_type.png", "t-SNE",
                        vectorizer, tsne, general_dir
                    )
                    
                    # Word importance visualization
                    if pca and hasattr(pca, 'components_'):
                        plot_word_importance(
                            vectorizer, pca, "TF-IDF",
                            "Important Terms Across All Documents", "overall_important_terms.png", general_dir
                        )
                    
                    # Create comparison visualizations
                    comparisons_dir = os.path.join(output_dir, "comparisons")
                    
                    # Plot term frequency distribution
                    plot_term_frequency_distribution(
                        tfidf_matrix, vectorizer,
                        "Term Frequency Distribution", "term_frequency.png", comparisons_dir
                    )
                    
                    # Network analysis if networkx is available
                    if NETWORKX_AVAILABLE:
                        try:
                            plot_term_network(
                                vectorizer, tfidf_matrix,
                                "Term Co-occurrence Network", "term_network.png", comparisons_dir
                            )
                        except Exception as net_error:
                            logger.error(f"Error creating term network: {str(net_error)}")
                    
                    # Create word cloud if available
                    if WORDCLOUD_AVAILABLE:
                        try:
                            create_word_cloud(
                                all_preprocessed, "Word Cloud for All Documents",
                                "overall_word_cloud.png", general_dir
                            )
                        except Exception as wc_error:
                            logger.error(f"Error creating overall word cloud: {str(wc_error)}")
                else:
                    logger.warning("Dimension reduction returned incomplete results for overall analysis")
            except Exception as e:
                logger.error(f"Error performing dimension reduction for overall analysis: {str(e)}")
                  
        except Exception as e:
            logger.error(f"Error during overall analysis: {str(e)}")
    
    logger.info(f"Analysis completed for {region_count} regions and {doc_count} documents")

@log_file_operation
def create_documents_summary(documents, filenames, regions, doc_types, output_dir):
    """
    Create a summary CSV file of all documents analyzed.
    
    Args:
        documents: List of document contents
        filenames: List of document filenames
        regions: List of regions associated with each document
        doc_types: List of document types
        output_dir: Directory to save the summary
    """
    try:
        # Count words in each document
        word_counts = [len(doc.split()) for doc in documents]
        content_lengths = [len(doc) for doc in documents]
        
        # Create a DataFrame
        summary_df = pd.DataFrame({
            'filename': filenames,
            'region': regions,
            'document_type': doc_types,
            'content_length': content_lengths,
            'word_count': word_counts
        })
        
        # Save to CSV
        summary_path = os.path.join(output_dir, 'document_summary.csv')
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Document summary created at {summary_path}")
        
        # Create region summary
        region_summary = summary_df.groupby('region').agg({
            'filename': 'count',
            'word_count': 'sum',
            'content_length': 'sum'
        }).reset_index()
        
        region_summary.columns = ['region', 'document_count', 'total_words', 'total_characters']
        
        # Save region summary
        region_summary_path = os.path.join(output_dir, 'region_summary.csv')
        region_summary.to_csv(region_summary_path, index=False)
        logger.info(f"Region summary created at {region_summary_path}")
        
        return summary_path
    except Exception as e:
        logger.error(f"Error creating document summary: {str(e)}")
        return None

# This implementation will be used if sklearn is not available
def perform_tfidf_and_dim_reduction_fallback(texts, region=None):
    """Fallback implementation that returns empty results but doesn't crash."""
    logger.warning("scikit-learn is not available. Cannot perform TF-IDF and dimension reduction.")
    return None, None, None, None, None, None

# Main TF-IDF and dimension reduction function
def perform_tfidf_and_dim_reduction(texts, region=None, min_df=2, max_df=0.95):
    """
    Perform TF-IDF vectorization and dimension reduction.
    
    Args:
        texts: List of preprocessed text documents.
        region: Optional region name for logging purposes.
        min_df: Minimum document frequency for TF-IDF.
        max_df: Maximum document frequency for TF-IDF.
        
    Returns:
        Tuple of (pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne)
        or None if an error occurs.
    """
    try:
        # Check if scikit-learn is available
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn is not available. Cannot perform TF-IDF and dimension reduction.")
            return None, None, None, None, None, None
            
        # Check if we have enough documents
        if len(texts) < 2:
            logger.warning("Need at least 2 documents for TF-IDF analysis")
            return None, None, None, None, None, None
            
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(max_features=1000, min_df=min_df, max_df=max_df)
        
        # Fit and transform documents
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ValueError as e:
            logger.error(f"Error in TF-IDF vectorization: {str(e)}")
            return None, None, None, None, None, None
            
        # Check if we have any features
        if tfidf_matrix.shape[1] == 0:
            logger.warning("No features extracted in TF-IDF vectorization")
            return None, None, None, None, None, None
            
        # Perform PCA
        try:
            pca = PCA(n_components=min(2, tfidf_matrix.shape[1], len(texts)-1))
            pca_result = pca.fit_transform(tfidf_matrix.toarray())
        except (ValueError, RuntimeWarning) as e:
            logger.error(f"Error in PCA: {str(e)}")
            pca = None
            pca_result = None
            
        # Perform LSA (Truncated SVD)
        try:
            lsa = TruncatedSVD(n_components=min(2, tfidf_matrix.shape[1], len(texts)-1))
            lsa_result = lsa.fit_transform(tfidf_matrix)
        except (ValueError, RuntimeWarning) as e:
            logger.error(f"Error in LSA: {str(e)}")
            lsa = None
            lsa_result = None
            
        # Perform t-SNE if we have enough documents
        try:
            if len(texts) >= 3:
                tsne = TSNE(n_components=min(2, 2), random_state=42)
                tsne_result = tsne.fit_transform(tfidf_matrix.toarray())
            else:
                logger.warning("Need at least 3 documents for t-SNE")
                tsne = None
                tsne_result = None
        except (ValueError, RuntimeWarning) as e:
            logger.error(f"Error in t-SNE: {str(e)}")
            tsne = None
            tsne_result = None
            
        return (pca_result, lsa_result, tsne_result, vectorizer, pca, lsa, tsne)
        
    except Exception as e:
        logger.error(f"Error in dimension reduction: {str(e)}")
        return None, None, None, None, None, None

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
