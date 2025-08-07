#!/usr/bin/env python3
"""
Test the updated book and poster prompts with comprehensive metrics and visualization
"""

import sys
import os
import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Add plotting imports
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    PLOTTING_AVAILABLE = True
except ImportError:
    print("⚠️  Plotting libraries not available. Install with: pip install matplotlib seaborn pandas")
    PLOTTING_AVAILABLE = False

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import SnlPoc

@dataclass
class TestMetrics:
    """Container for individual test metrics"""
    query: str
    category: str
    response_time: float
    response_length: int
    word_count: int
    success: bool
    validation_results: Dict[str, bool] = field(default_factory=dict)
    content_quality: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    response_content: str = ""  # Store the actual response text

class QuestionParser:
    """Handles parsing and categorizing questions from test_questions.txt"""
    
    def __init__(self, questions_file: str):
        self.questions_file = questions_file
    
    def load_questions(self) -> List[Tuple[str, str]]:
        """Load and categorize questions from file"""
        if not os.path.exists(self.questions_file):
            print(f"❌ Questions file not found: {self.questions_file}")
            return []
        
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        questions = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Each non-empty line is a question
            # Try to categorize based on content keywords
            category = self._categorize_question(line)
            questions.append((line, category))
        
        return questions
    
    def _categorize_question(self, question: str) -> str:
        """Categorize a question based on its content"""
        question_lower = question.lower()
        
        # Library info questions
        if any(keyword in question_lower for keyword in ['opening hours', 'open', 'fee', 'wi-fi', 'cafeteria']):
            return "Library Information"
        
        # Contact questions
        if any(keyword in question_lower for keyword in ['phone', 'address', 'located', 'contact']):
            return "Contact & Location"
        
        # Service questions
        if any(keyword in question_lower for keyword in ['request', 'borrow', 'loan', 'print', 'scan', 'photocopy', 'help', 'research']):
            return "Services"
        
        # Navigation questions
        if any(keyword in question_lower for keyword in ['where can i find', 'which page', 'search', 'catalogue']):
            return "Site Navigation"
        
        # Thesis questions
        if any(keyword in question_lower for keyword in ['thesis', 'theses', 'phd', 'dissertation', 'abstract']):
            return "Thesis Research"
        
        # Poster questions
        if any(keyword in question_lower for keyword in ['poster', 'designed', 'printed', 'exhibition', 'dimensions']):
            return "Poster Research"
        
        # Default category
        return "General"

class MetricsCollector:
    """Handles collection and analysis of test metrics"""
    
    def __init__(self):
        self.metrics: List[TestMetrics] = []
    
    def validate_response(self, response: str, expected_type: str = None) -> Dict[str, bool]:
        """Validate response format and content"""
        validation = {}
        
        # Link format validation
        validation['has_primary_source'] = '[PRIMARY_SOURCE:' in response
        validation['has_poster_page'] = '[POSTER_PAGE:' in response
        validation['has_poster_image'] = '[POSTER_IMAGE:' in response
        
        # Content validation
        validation['has_specific_info'] = any(keyword in response.lower() for keyword in 
                                            ['phone', 'address', 'hour', 'fee', 'available', 'collection'])
        validation['has_structured_answer'] = len(response.split('\n')) > 1
        validation['appropriate_length'] = 50 < len(response) < 2000
        
        return validation
    
    def analyze_content_quality(self, query: str, response: str) -> Dict[str, Any]:
        """Analyze content quality metrics"""
        quality = {}
        
        # Basic metrics
        quality['relevance_keywords'] = self._count_query_keywords(query, response)
        quality['has_dates'] = bool(re.search(r'\d{4}|\d{1,2}[:./]\d{1,2}', response))
        quality['has_numbers'] = bool(re.search(r'\d+', response))
        quality['has_contact_info'] = bool(re.search(r'@|\+\d|\d{3}[-.\s]\d{3}', response))
        
        # Domain-specific analysis
        if 'poster' in query.lower():
            quality['poster_specific'] = any(term in response.lower() for term in 
                                           ['exhibition', 'design', 'print', 'dimension', 'format'])
        elif 'book' in query.lower():
            quality['book_specific'] = any(term in response.lower() for term in 
                                         ['author', 'publisher', 'isbn', 'available', 'borrow'])
        elif 'thesis' in query.lower():
            quality['thesis_specific'] = any(term in response.lower() for term in 
                                           ['research', 'university', 'advisor', 'abstract'])
        
        return quality
    
    def _count_query_keywords(self, query: str, response: str) -> int:
        """Count how many query keywords appear in response"""
        query_words = set(word.lower().strip('?."') for word in query.split() if len(word) > 3)
        response_words = set(word.lower().strip('?."') for word in response.split())
        return len(query_words.intersection(response_words))

# Visualization and analysis classes will be added once plotting libraries are available

class TestVisualizer:
    """Handles visualization and plotting of test results"""
    
    def __init__(self, output_dir: str = "output"):
        self.base_output_dir = output_dir
        # Create a unique run folder with timestamp
        self.run_timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, f"run_{self.run_timestamp}")
        self._ensure_output_dir()
        
        # Set up matplotlib for non-interactive backend (for Docker/servers)
        plt.switch_backend('Agg')
        
        # Set style
        plt.style.use('default')
        sns.set_palette("husl")
        
        print(f"📁 Test run folder created: {self.output_dir}")
    
    def _ensure_output_dir(self):
        """Ensure output directory and run-specific folder exist"""
        os.makedirs(self.base_output_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _save_plot(self, filename: str, dpi: int = 300):
        """Save current plot with run timestamp"""
        base_name = filename.replace('.png', '').replace('.jpg', '')
        full_path = os.path.join(self.output_dir, f"{base_name}.png")
        plt.savefig(full_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        plt.close()  # Close to free memory
        print(f"📊 Plot saved: {full_path}")
        return full_path
    
    def plot_response_times(self, metrics: List[TestMetrics]):
        """Plot response time distribution by category"""
        if not metrics:
            print("⚠️ No metrics to plot")
            return
        
        df = pd.DataFrame([
            {
                'category': m.category,
                'response_time': m.response_time,
                'success': m.success
            } for m in metrics
        ])
        
        plt.figure(figsize=(12, 8))
        
        # Response time boxplot by category
        plt.subplot(2, 2, 1)
        sns.boxplot(data=df, x='category', y='response_time')
        plt.title('Response Time Distribution by Category')
        plt.xticks(rotation=45)
        plt.ylabel('Response Time (seconds)')
        
        # Response time histogram
        plt.subplot(2, 2, 2)
        plt.hist(df['response_time'], bins=20, alpha=0.7, edgecolor='black')
        plt.title('Overall Response Time Distribution')
        plt.xlabel('Response Time (seconds)')
        plt.ylabel('Frequency')
        
        # Success rate by category
        plt.subplot(2, 2, 3)
        success_rate = df.groupby('category')['success'].mean().sort_values(ascending=False)
        success_rate.plot(kind='bar', color='skyblue')
        plt.title('Success Rate by Category')
        plt.ylabel('Success Rate')
        plt.xticks(rotation=45)
        
        # Average response time by category
        plt.subplot(2, 2, 4)
        avg_times = df.groupby('category')['response_time'].mean().sort_values(ascending=False)
        avg_times.plot(kind='bar', color='lightcoral')
        plt.title('Average Response Time by Category')
        plt.ylabel('Average Time (seconds)')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._save_plot('response_times_analysis.png')
    
    def plot_content_quality(self, metrics: List[TestMetrics]):
        """Plot content quality metrics"""
        if not metrics:
            print("⚠️ No metrics to plot")
            return
        
        # Extract quality metrics
        quality_data = []
        for m in metrics:
            for key, value in m.content_quality.items():
                if isinstance(value, bool):
                    quality_data.append({
                        'metric': key,
                        'value': value,
                        'category': m.category
                    })
        
        if not quality_data:
            print("⚠️ No quality metrics to plot")
            return
        
        df = pd.DataFrame(quality_data)
        
        plt.figure(figsize=(15, 10))
        
        # Quality metrics heatmap
        plt.subplot(2, 2, 1)
        quality_matrix = df.groupby(['category', 'metric'])['value'].mean().unstack(fill_value=0)
        sns.heatmap(quality_matrix, annot=True, cmap='RdYlGn', center=0.5, fmt='.2f')
        plt.title('Content Quality Metrics by Category')
        
        # Overall quality score
        plt.subplot(2, 2, 2)
        overall_quality = df.groupby('metric')['value'].mean().sort_values(ascending=False)
        overall_quality.plot(kind='bar', color='lightgreen')
        plt.title('Overall Quality Metrics Performance')
        plt.ylabel('Success Rate')
        plt.xticks(rotation=45)
        
        # Response length distribution
        plt.subplot(2, 2, 3)
        lengths = [m.response_length for m in metrics]
        plt.hist(lengths, bins=20, alpha=0.7, edgecolor='black', color='orange')
        plt.title('Response Length Distribution')
        plt.xlabel('Response Length (characters)')
        plt.ylabel('Frequency')
        
        # Word count distribution
        plt.subplot(2, 2, 4)
        word_counts = [m.word_count for m in metrics]
        plt.hist(word_counts, bins=20, alpha=0.7, edgecolor='black', color='purple')
        plt.title('Word Count Distribution')
        plt.xlabel('Word Count')
        plt.ylabel('Frequency')
        
        plt.tight_layout()
        return self._save_plot('content_quality_analysis.png')
    
    def plot_validation_results(self, metrics: List[TestMetrics]):
        """Plot validation results"""
        if not metrics:
            print("⚠️ No metrics to plot")
            return
        
        # Extract validation metrics
        validation_data = []
        for m in metrics:
            for key, value in m.validation_results.items():
                validation_data.append({
                    'validation': key,
                    'passed': value,
                    'category': m.category
                })
        
        if not validation_data:
            print("⚠️ No validation metrics to plot")
            return
        
        df = pd.DataFrame(validation_data)
        
        plt.figure(figsize=(12, 8))
        
        # Validation pass rate by category
        plt.subplot(2, 2, 1)
        validation_rate = df.groupby(['category', 'validation'])['passed'].mean().unstack(fill_value=0)
        sns.heatmap(validation_rate, annot=True, cmap='RdYlGn', center=0.5, fmt='.2f')
        plt.title('Validation Pass Rate by Category')
        
        # Overall validation performance
        plt.subplot(2, 2, 2)
        overall_validation = df.groupby('validation')['passed'].mean().sort_values(ascending=False)
        overall_validation.plot(kind='bar', color='gold')
        plt.title('Overall Validation Performance')
        plt.ylabel('Pass Rate')
        plt.xticks(rotation=45)
        
        # Success vs validation correlation
        plt.subplot(2, 2, 3)
        success_validation = []
        for m in metrics:
            if m.validation_results:
                avg_validation = sum(m.validation_results.values()) / len(m.validation_results)
                success_validation.append({
                    'success': m.success,
                    'avg_validation': avg_validation,
                    'category': m.category
                })
        
        if success_validation:
            sv_df = pd.DataFrame(success_validation)
            plt.scatter(sv_df['avg_validation'], sv_df['success'], alpha=0.6)
            plt.xlabel('Average Validation Score')
            plt.ylabel('Success (1=Yes, 0=No)')
            plt.title('Success vs Validation Correlation')
        
        # Category performance summary
        plt.subplot(2, 2, 4)
        category_summary = df.groupby('category')['passed'].mean().sort_values(ascending=False)
        category_summary.plot(kind='bar', color='lightblue')
        plt.title('Category Performance Summary')
        plt.ylabel('Average Pass Rate')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._save_plot('validation_results_analysis.png')
    
    def generate_summary_report(self, metrics: List[TestMetrics]) -> str:
        """Generate a comprehensive summary report"""
        if not metrics:
            return "No metrics available for report generation"
        
        df = pd.DataFrame([
            {
                'category': m.category,
                'response_time': m.response_time,
                'response_length': m.response_length,
                'word_count': m.word_count,
                'success': m.success,
                'query': m.query
            } for m in metrics
        ])
        
        report = []
        report.append("# Test Results Summary Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Tests: {len(metrics)}")
        report.append("")
        
        # Overall statistics
        report.append("## Overall Statistics")
        report.append(f"- Average Response Time: {df['response_time'].mean():.2f} seconds")
        report.append(f"- Median Response Time: {df['response_time'].median():.2f} seconds")
        report.append(f"- Success Rate: {df['success'].mean():.1%}")
        report.append(f"- Average Response Length: {df['response_length'].mean():.0f} characters")
        report.append(f"- Average Word Count: {df['word_count'].mean():.0f} words")
        report.append("")
        
        # Category breakdown
        report.append("## Performance by Category")
        category_stats = df.groupby('category').agg({
            'response_time': ['mean', 'median', 'count'],
            'success': 'mean',
            'response_length': 'mean',
            'word_count': 'mean'
        }).round(2)
        
        for category in category_stats.index:
            stats = category_stats.loc[category]
            report.append(f"### {category}")
            report.append(f"- Count: {stats[('response_time', 'count')]}")
            report.append(f"- Success Rate: {stats[('success', 'mean')]:.1%}")
            report.append(f"- Avg Response Time: {stats[('response_time', 'mean')]:.2f}s")
            report.append(f"- Avg Length: {stats[('response_length', 'mean')]:.0f} chars")
            report.append("")
        
        # Detailed questions table
        report.append("## Detailed Results by Question")
        report.append("")
        report.append("| # | Status | Question | Category | Time (s) | Length | Words |")
        report.append("|---|--------|----------|----------|----------|--------|-------|")
        
        for i, metric in enumerate(metrics, 1):
            # Status icon
            status_icon = "✅" if metric.success else "❌"
            if metric.error_message:
                status_icon = "🔥"  # Fire emoji for errors
            
            # Truncate question for table display
            question_display = metric.query[:50] + "..." if len(metric.query) > 50 else metric.query
            question_display = question_display.replace("|", "\\|")  # Escape pipes for markdown
            
            # Format category
            category_display = metric.category.replace("|", "\\|")
            
            report.append(f"| {i:2d} | {status_icon} | {question_display} | {category_display} | {metric.response_time:.2f} | {metric.response_length} | {metric.word_count} |")
        
        report.append("")
        report.append("**Legend:**")
        report.append("- ✅ Success")
        report.append("- ❌ Failed")
        report.append("- 🔥 Error occurred")
        
        # Save main report
        report_path = os.path.join(self.output_dir, f"test_summary_report.md")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"📋 Report saved: {report_path}")
        
        # Generate detailed Q&A file
        qa_report_path = self._generate_detailed_qa_report(metrics)
        print(f"📄 Detailed Q&A saved: {qa_report_path}")
        
        return report_path
    
    def _generate_detailed_qa_report(self, metrics: List[TestMetrics]) -> str:
        """Generate a detailed question-answer report for manual review"""
        qa_report = []
        qa_report.append("# Detailed Question & Answer Report")
        qa_report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        qa_report.append(f"Total Questions: {len(metrics)}")
        qa_report.append("")
        qa_report.append("---")
        qa_report.append("")
        
        for i, metric in enumerate(metrics, 1):
            # Status information
            status_icon = "✅ SUCCESS" if metric.success else "❌ FAILED"
            if metric.error_message:
                status_icon = "🔥 ERROR"
            
            qa_report.append(f"## Question {i}: {status_icon}")
            qa_report.append("")
            qa_report.append(f"**Category:** {metric.category}")
            qa_report.append(f"**Response Time:** {metric.response_time:.2f} seconds")
            qa_report.append(f"**Response Length:** {metric.response_length} characters")
            qa_report.append(f"**Word Count:** {metric.word_count} words")
            qa_report.append("")
            
            # Question
            qa_report.append("### 🤔 Question:")
            qa_report.append(f"```")
            qa_report.append(metric.query)
            qa_report.append(f"```")
            qa_report.append("")
            
            # Answer or error
            if metric.error_message:
                qa_report.append("### 🔥 Error:")
                qa_report.append(f"```")
                qa_report.append(metric.error_message)
                qa_report.append(f"```")
            else:
                qa_report.append("### 💬 Response:")
                qa_report.append(f"```")
                qa_report.append(metric.response_content if metric.response_content else "(No response content available)")
                qa_report.append(f"```")
            
            qa_report.append("")
            
            # Validation results if available
            if metric.validation_results:
                qa_report.append("### 🔍 Validation Results:")
                for validation_type, passed in metric.validation_results.items():
                    icon = "✅" if passed else "❌"
                    qa_report.append(f"- {icon} {validation_type}")
                qa_report.append("")
            
            # Content quality if available
            if metric.content_quality:
                qa_report.append("### 📊 Content Quality:")
                for quality_type, value in metric.content_quality.items():
                    if isinstance(value, bool):
                        icon = "✅" if value else "❌"
                        qa_report.append(f"- {icon} {quality_type}")
                    else:
                        qa_report.append(f"- {quality_type}: {value}")
                qa_report.append("")
            
            qa_report.append("---")
            qa_report.append("")
        
        # Save detailed report
        qa_report_path = os.path.join(self.output_dir, f"detailed_qa_report.md")
        
        with open(qa_report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(qa_report))
        
        return qa_report_path
    
    def create_run_info_file(self, total_questions: int, actual_tested: int, start_time: float) -> str:
        """Create a run information file with metadata about the test session"""
        end_time = time.time()
        total_duration = end_time - start_time
        
        run_info = []
        run_info.append("# Test Run Information")
        run_info.append(f"**Run ID:** run_{self.run_timestamp}")
        run_info.append(f"**Start Time:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        run_info.append(f"**End Time:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
        run_info.append(f"**Total Duration:** {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
        run_info.append("")
        run_info.append("## Test Configuration")
        run_info.append(f"- **Total Questions Available:** {total_questions}")
        run_info.append(f"- **Questions Actually Tested:** {actual_tested}")
        run_info.append(f"- **Coverage:** {actual_tested/total_questions*100:.1f}%")
        run_info.append("")
        run_info.append("## Generated Files")
        run_info.append("- `test_summary_report.md` - Executive summary with question table")
        run_info.append("- `detailed_qa_report.md` - Complete question-answer pairs")
        run_info.append("- `response_times_analysis.png` - Response time visualizations")
        run_info.append("- `content_quality_analysis.png` - Content quality metrics")
        run_info.append("- `validation_results_analysis.png` - Validation results")
        run_info.append("")
        run_info.append("## System Info")
        run_info.append(f"- **Python Version:** {sys.version.split()[0]}")
        run_info.append(f"- **Working Directory:** {os.getcwd()}")
        run_info.append(f"- **Output Directory:** {self.output_dir}")
        
        # Save run info file
        run_info_path = os.path.join(self.output_dir, "run_info.md")
        with open(run_info_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(run_info))
        
        print(f"📋 Run info saved: {run_info_path}")
        return run_info_path

# Comprehensive test runner will be added once plotting libraries are available

def run_comprehensive_test(questions: List[Tuple[str, str]], max_questions: int = None) -> List[TestMetrics]:
    """Run comprehensive testing on all questions with metrics collection and visualization"""
    
    if not PLOTTING_AVAILABLE:
        print("❌ Plotting libraries not available. Cannot run comprehensive test.")
        return []
    
    # Track test run timing and metadata
    test_start_time = time.time()
    total_questions = len(questions)
    
    print("🚀 Starting Comprehensive Test Suite")
    print("=" * 50)
    
    # Initialize components
    crew = SnlPoc()
    metrics_collector = MetricsCollector()
    visualizer = TestVisualizer()
    
    # Limit questions if specified
    if max_questions:
        questions = questions[:max_questions]
        print(f"📝 Testing {len(questions)} questions (limited from total {total_questions})")
    else:
        print(f"📝 Testing all {len(questions)} questions")
    
    # Run tests
    for i, (question, category) in enumerate(questions, 1):
        print(f"\n[{i:3d}/{len(questions)}] Testing: {question[:60]}...")
        print(f"    Category: {category}")
        
        start_time = time.time()
        
        try:
            # Get response
            response = crew.chat(question)
            response_time = time.time() - start_time
            
            # Calculate metrics
            response_length = len(response)
            word_count = len(response.split())
            
            # Validate response
            validation_results = metrics_collector.validate_response(response)
            
            # Analyze content quality
            content_quality = metrics_collector.analyze_content_quality(question, response)
            
            # Determine success (basic heuristic)
            success = (
                response_length > 50 and  # Not too short
                response_length < 5000 and  # Not too long
                not any(error in response.lower() for error in ['error', 'sorry', 'cannot', 'unable'])
            )
            
            # Create metrics object
            metric = TestMetrics(
                query=question,
                category=category,
                response_time=response_time,
                response_length=response_length,
                word_count=word_count,
                success=success,
                validation_results=validation_results,
                content_quality=content_quality,
                response_content=response
            )
            
            metrics_collector.metrics.append(metric)
            
            # Show progress
            status = "✅" if success else "⚠️"
            print(f"    {status} {response_time:.2f}s | {response_length} chars | {word_count} words")
            
        except Exception as e:
            response_time = time.time() - start_time
            print(f"    ❌ Error: {e}")
            
            # Create error metric
            metric = TestMetrics(
                query=question,
                category=category,
                response_time=response_time,
                response_length=0,
                word_count=0,
                success=False,
                error_message=str(e),
                response_content=""
            )
            metrics_collector.metrics.append(metric)
        
        # Progress indicator
        if i % 10 == 0:
            print(f"    📊 Progress: {i}/{len(questions)} ({i/len(questions)*100:.1f}%)")
    
    print(f"\n✅ Comprehensive testing complete!")
    print(f"📊 Collected metrics for {len(metrics_collector.metrics)} tests")
    
    # Generate visualizations
    if metrics_collector.metrics:
        print("\n📈 Generating visualizations...")
        
        # Response time analysis
        visualizer.plot_response_times(metrics_collector.metrics)
        
        # Content quality analysis
        visualizer.plot_content_quality(metrics_collector.metrics)
        
        # Validation results
        visualizer.plot_validation_results(metrics_collector.metrics)
        
        # Generate summary report
        report_path = visualizer.generate_summary_report(metrics_collector.metrics)
        
        # Create run info file
        visualizer.create_run_info_file(total_questions, len(metrics_collector.metrics), test_start_time)
        
        print(f"\n📋 All outputs saved to: {visualizer.output_dir}/")
        print(f"📄 Summary report: {report_path}")
    
    return metrics_collector.metrics

def test_new_prompts():
    """Test the updated prompts for books and posters"""
    
    print("🧪 Testing Updated Book and Poster Prompts")
    print("=" * 50)
    
    # Initialize the crew
    crew = SnlPoc()
    
    # Test queries
    test_queries = [
        ("Find books by Van Gogh", "books"),
        ("Van Gogh exhibition posters", "posters"),
    ]
    
    for query, expected_type in test_queries:
        print(f"\n💬 Testing: '{query}'")
        print(f"Expected type: {expected_type}")
        print("-" * 40)
        
        try:
            # Get response
            response = crew.chat(query)
            
            print("Response:")
            print(response)
            
            # Check for expected link formats
            if expected_type == "books":
                if "[PRIMARY_SOURCE:" in response:
                    print("✅ Found PRIMARY_SOURCE link for books")
                else:
                    print("❌ Missing PRIMARY_SOURCE link for books")
                    
            elif expected_type == "posters":
                poster_page_found = "[POSTER_PAGE:" in response
                poster_image_found = "[POSTER_IMAGE:" in response
                
                if poster_page_found and poster_image_found:
                    print("✅ Found both POSTER_PAGE and POSTER_IMAGE links")
                elif poster_page_found:
                    print("⚠️ Found POSTER_PAGE but missing POSTER_IMAGE")
                elif poster_image_found:
                    print("⚠️ Found POSTER_IMAGE but missing POSTER_PAGE")
                else:
                    print("❌ Missing both poster link types")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n✅ Testing complete!")

def test_question_parsing():
    """Test the question parsing functionality"""
    print("🔍 Testing Question Parsing")
    print("-" * 30)
    
    parser = QuestionParser("test_questions.txt")
    
    # Debug: Show file content parsing
    with open("test_questions.txt", 'r', encoding='utf-8') as f:
        lines = f.readlines()[:10]  # First 10 lines
    
    print("📄 First 10 lines of file:")
    for i, line in enumerate(lines, 1):
        line_clean = line.strip()
        print(f"   {i:2d}: '{line_clean}'")
        
        # Show what our parser logic detects
        if line_clean.startswith('o "'):
            print(f"       → DETECTED AS QUESTION")
        elif (line_clean and not line_clean.startswith('o ') and 
              (re.match(r'^\d+\.\s', line_clean) or re.match(r'^[A-Z]\)\s', line_clean) or 
               any(keyword in line_clean.lower() for keyword in ['practical', 'contact', 'service', 'navigation', 'finding', 'deep q&a', 'global search']))):
            print(f"       → DETECTED AS CATEGORY")
    
    questions = parser.load_questions()
    
    print(f"\n📝 Found {len(questions)} questions")
    
    # Group by category
    by_category = {}
    for question, category in questions:
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(question)
    
    # Show summary
    for category, qs in by_category.items():
        print(f"\n📂 {category}: {len(qs)} questions")
        # Show first question as example
        if qs:
            print(f"   Example: {qs[0][:60]}...")
    
    return questions

if __name__ == "__main__":
    # Test question parsing first
    questions = test_question_parsing()
    
    print(f"\n{'='*50}")
    print("Would you like to:")
    print("1. Run basic prompts test")  
    print("2. Run comprehensive test on all questions")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice in ["1", "3"]:
        test_new_prompts()
    
    if choice in ["2", "3"]:
        if questions:
            print(f"\n🚀 Running comprehensive test on {len(questions)} questions...")
            print("💡 Tip: You can limit the number of questions by editing the max_questions parameter")
            
            # Ask if user wants to limit questions for testing
            limit_input = input("Enter max questions to test (or press Enter for all): ").strip()
            max_questions = int(limit_input) if limit_input.isdigit() else None
            
            metrics = run_comprehensive_test(questions, max_questions)
            
            if metrics:
                print(f"\n🎉 Comprehensive testing complete!")
                print(f"📊 Processed {len(metrics)} questions")
                print(f"📈 Generated visualizations and reports in output/ directory")
        else:
            print("❌ No questions loaded. Cannot run comprehensive test.")