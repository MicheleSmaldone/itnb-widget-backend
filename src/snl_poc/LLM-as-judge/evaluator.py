import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Data class for evaluation results"""
    query_id: int
    query: str
    response: str
    answered_query: Dict[str, Any]
    source_format: Dict[str, Any] 
    chatbot_quality: Dict[str, Any]
    overall_score: float
    timestamp: str

class LLMJudgeEvaluator:
    """LLM-as-Judge evaluator for chatbot responses"""
    
    def __init__(self):
        """Initialize the evaluator with OpenAI client"""
        # Initialize OpenAI client

        if not os.getenv("OPENAI_API_BASE") or not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_* not found in environment variables")

        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE")  # Optional for custom endpoints
        )
        
        # Fix model name - remove "openai/" prefix if present
        raw_model = os.getenv("OPENAI_MODEL_NAME")
        if raw_model and raw_model.startswith("openai/"):
            self.model = raw_model.replace("openai/", "")
        else:
            self.model = raw_model
        
        logger.info(f"Initialized LLM Judge with model: {self.model} (raw: {raw_model})")
    
    def evaluate_response(self, query: str, response: str, groundx_context: str = "") -> EvaluationResult:
        """Evaluate a single response against the three criteria"""
        
        # Criterion 1: Did the agent answer the user's query?
        answered_query = self._evaluate_query_answered(query, response)
        
        # Criterion 2: Were links provided in the right [PRIMARY_SOURCE: URL] format?
        source_format = self._evaluate_source_format(response)
        
        # Criterion 3: Is the answer pleasant for a chatbot on a website?
        chatbot_quality = self._evaluate_chatbot_quality(query, response)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(answered_query, source_format, chatbot_quality)
        
        return EvaluationResult(
            query_id=0,  # Will be set externally
            query=query,
            response=response,
            answered_query=answered_query,
            source_format=source_format,
            chatbot_quality=chatbot_quality,
            overall_score=overall_score,
            timestamp=datetime.now().isoformat()
        )
    
    def _evaluate_query_answered(self, query: str, response: str) -> Dict[str, Any]:
        """Evaluate if the agent answered the user's query"""
        
        prompt = f"""
You are evaluating whether a chatbot response adequately answers the user's question.

USER QUERY: "{query}"

CHATBOT RESPONSE: "{response}"

Evaluate on these aspects:
1. RELEVANCE: Does the response address the specific question asked?
2. COMPLETENESS: Does it provide sufficient information to answer the query?
3. ACCURACY: Based on the response content, does it seem accurate and factual?

Rate each aspect from 1-5 (1=Poor, 2=Below Average, 3=Average, 4=Good, 5=Excellent)

Respond in this exact JSON format:
{{
    "relevance_score": <1-5>,
    "completeness_score": <1-5>, 
    "accuracy_score": <1-5>,
    "overall_answered": <1-5>,
    "explanation": "<brief explanation of scoring>"
}}
"""
        
        try:
            response_obj = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result = json.loads(response_obj.choices[0].message.content)
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating query answered: {str(e)}")
            return {
                "relevance_score": 0,
                "completeness_score": 0,
                "accuracy_score": 0,
                "overall_answered": 0,
                "explanation": f"Evaluation failed: {str(e)}",
                "success": False
            }
    
    def _evaluate_source_format(self, response: str) -> Dict[str, Any]:
        """Evaluate if sources are provided in the correct [PRIMARY_SOURCE: URL] format"""
        
        # Check for [PRIMARY_SOURCE: URL] pattern
        primary_source_pattern = r'\[PRIMARY_SOURCE:\s*([^\]]+)\]'
        primary_sources = re.findall(primary_source_pattern, response)
        
        # Check for incorrect formats
        wrong_formats = []
        
        # Check for [SOURCE: URL] (incorrect)
        source_pattern = r'\[SOURCE:\s*([^\]]+)\]'
        if re.search(source_pattern, response):
            wrong_formats.append("Found [SOURCE: URL] instead of [PRIMARY_SOURCE: URL]")
        
        # Check for other citation formats
        other_citations = re.findall(r'\[[^\]]*(?:http|www)[^\]]*\]', response)
        for citation in other_citations:
            if not re.match(primary_source_pattern, citation):
                wrong_formats.append(f"Incorrect citation format: {citation}")
        
        # Calculate score
        if primary_sources and not wrong_formats:
            score = 5  # Perfect format
        elif primary_sources and wrong_formats:
            score = 3  # Has correct sources but also wrong formats
        elif not primary_sources and not wrong_formats:
            score = 2  # No sources (might be acceptable if none available)
        else:
            score = 1  # Only wrong formats
        
        return {
            "score": score,
            "primary_sources_found": len(primary_sources),
            "primary_sources": primary_sources,
            "wrong_formats": wrong_formats,
            "has_correct_format": len(primary_sources) > 0,
            "has_wrong_format": len(wrong_formats) > 0,
            "explanation": f"Found {len(primary_sources)} correct PRIMARY_SOURCE citations, {len(wrong_formats)} format errors"
        }
    
    def _evaluate_chatbot_quality(self, query: str, response: str) -> Dict[str, Any]:
        """Evaluate if the response is pleasant and appropriate for a website chatbot"""
        
        prompt = f"""
You are evaluating the quality of a chatbot response for a library website.

USER QUERY: "{query}"

CHATBOT RESPONSE: "{response}"

Evaluate the response on these criteria for a professional library website chatbot:

1. TONE: Is the tone professional, friendly, and helpful?
2. CLARITY: Is the response clear and easy to understand?
3. CONCISENESS: Is it appropriately concise (around 50-100 words as expected)?
4. PROFESSIONALISM: Does it maintain professional standards for a library?
5. USER EXPERIENCE: Would this response satisfy a website visitor?

Rate each aspect from 1-5 (1=Poor, 2=Below Average, 3=Average, 4=Good, 5=Excellent)

Respond in this exact JSON format:
{{
    "tone_score": <1-5>,
    "clarity_score": <1-5>,
    "conciseness_score": <1-5>,
    "professionalism_score": <1-5>,
    "user_experience_score": <1-5>,
    "overall_quality": <1-5>,
    "word_count": <actual word count>,
    "explanation": "<brief explanation of scoring>"
}}
"""
        
        try:
            response_obj = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result = json.loads(response_obj.choices[0].message.content)
            
            # Add actual word count
            word_count = len(response.split())
            result["actual_word_count"] = word_count
            result["word_count_appropriate"] = 50 <= word_count <= 100
            result["success"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating chatbot quality: {str(e)}")
            return {
                "tone_score": 0,
                "clarity_score": 0,
                "conciseness_score": 0,
                "professionalism_score": 0,
                "user_experience_score": 0,
                "overall_quality": 0,
                "word_count": len(response.split()),
                "actual_word_count": len(response.split()),
                "word_count_appropriate": False,
                "explanation": f"Evaluation failed: {str(e)}",
                "success": False
            }
    
    def _calculate_overall_score(self, answered_query: Dict, source_format: Dict, chatbot_quality: Dict) -> float:
        """Calculate overall score weighted across all criteria"""
        
        # Weights for each criterion
        query_weight = 0.5  # Most important: did it answer the question?
        format_weight = 0.2  # Important: proper citation format
        quality_weight = 0.3  # Important: overall user experience
        
        # Get scores (out of 5)
        query_score = answered_query.get("overall_answered", 0)
        format_score = source_format.get("score", 0) 
        quality_score = chatbot_quality.get("overall_quality", 0)
        
        # Calculate weighted average (convert to 0-100 scale)
        overall = (
            query_score * query_weight + 
            format_score * format_weight + 
            quality_score * quality_weight
        ) * 20  # Convert from 0-5 scale to 0-100 scale
        
        return round(overall, 1)
    
    def evaluate_batch(self, queries_file: str = None) -> List[EvaluationResult]:
        """Evaluate a batch of queries from the queries.json file"""
        
        if queries_file is None:
            queries_file = os.path.join(os.path.dirname(__file__), "queries.json")
        
        # Load queries
        with open(queries_file, 'r') as f:
            data = json.load(f)
        
        results = []
        
        for query_data in data["test_queries"]:
            logger.info(f"Evaluating query {query_data['id']}: {query_data['query'][:50]}...")
            
            # You would replace this with actual response from your RAG system
            # For now, using a placeholder
            sample_response = "This is a sample response that would come from your RAG system."
            
            result = self.evaluate_response(query_data["query"], sample_response)
            result.query_id = query_data["id"]
            
            results.append(result)
        
        return results
    
    def save_results(self, results: List[EvaluationResult], output_dir: str = None):
        """Save evaluation results to JSON file"""
        
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "eval_results")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert results to dictionary format
        results_dict = {
            "evaluation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
                "total_queries": len(results),
                "average_score": sum(r.overall_score for r in results) / len(results) if results else 0
            },
            "results": [
                {
                    "query_id": r.query_id,
                    "query": r.query,
                    "response": r.response,
                    "scores": {
                        "answered_query": r.answered_query,
                        "source_format": r.source_format,
                        "chatbot_quality": r.chatbot_quality,
                        "overall_score": r.overall_score
                    },
                    "timestamp": r.timestamp
                }
                for r in results
            ]
        }
        
        # Save detailed results
        output_file = os.path.join(output_dir, f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        
        # Generate summary report
        self._generate_summary_report(results_dict, output_dir)
        
        return output_file
    
    def _generate_summary_report(self, results_dict: Dict, output_dir: str):
        """Generate a human-readable summary report"""
        
        results = results_dict["results"]
        metadata = results_dict["evaluation_metadata"]
        
        summary = f"""# LLM-as-Judge Evaluation Report

## Summary
- **Evaluation Date**: {metadata['timestamp']}
- **Model Used**: {metadata['model']}
- **Total Queries**: {metadata['total_queries']}
- **Average Overall Score**: {metadata['average_score']:.1f}/100

## Score Breakdown

### Overall Scores Distribution
"""
        
        # Score distribution
        score_ranges = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "Below 60": 0}
        for result in results:
            score = result["scores"]["overall_score"]
            if score >= 90:
                score_ranges["90-100"] += 1
            elif score >= 80:
                score_ranges["80-89"] += 1
            elif score >= 70:
                score_ranges["70-79"] += 1
            elif score >= 60:
                score_ranges["60-69"] += 1
            else:
                score_ranges["Below 60"] += 1
        
        for range_name, count in score_ranges.items():
            percentage = (count / len(results)) * 100 if results else 0
            summary += f"- **{range_name}**: {count} queries ({percentage:.1f}%)\n"
        
        summary += "\n### Criteria Averages\n"
        
        # Calculate averages for each criterion
        if results:
            avg_query_answered = sum(r["scores"]["answered_query"]["overall_answered"] for r in results) / len(results)
            avg_source_format = sum(r["scores"]["source_format"]["score"] for r in results) / len(results)
            avg_chatbot_quality = sum(r["scores"]["chatbot_quality"]["overall_quality"] for r in results) / len(results)
            
            summary += f"- **Query Answered**: {avg_query_answered:.1f}/5\n"
            summary += f"- **Source Format**: {avg_source_format:.1f}/5\n"
            summary += f"- **Chatbot Quality**: {avg_chatbot_quality:.1f}/5\n"
        
        summary += "\n### Individual Results\n\n"
        
        for result in results:
            scores = result["scores"]
            summary += f"""**Query {result['query_id']}**: {result['query'][:60]}...
- Overall Score: {scores['overall_score']}/100
- Query Answered: {scores['answered_query']['overall_answered']}/5
- Source Format: {scores['source_format']['score']}/5
- Chatbot Quality: {scores['chatbot_quality']['overall_quality']}/5

"""
        
        # Save summary
        summary_file = os.path.join(output_dir, f"evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(summary_file, 'w') as f:
            f.write(summary)
        
        logger.info(f"Summary report saved to: {summary_file}")

# Example usage
if __name__ == "__main__":
    evaluator = LLMJudgeEvaluator()
    
    # Example single evaluation
    query = "What are the library's opening hours?"
    response = "The library's opening hours are Monday to Friday, 9 a.m. – 6 p.m. [PRIMARY_SOURCE: https://www.nb.admin.ch/snl/en/home/about-us/opening-hours.html]"
    
    result = evaluator.evaluate_response(query, response)
    print(f"Overall Score: {result.overall_score}/100")
    print(f"Query Answered: {result.answered_query['overall_answered']}/5")
    print(f"Source Format: {result.source_format['score']}/5") 
    print(f"Chatbot Quality: {result.chatbot_quality['overall_quality']}/5")
