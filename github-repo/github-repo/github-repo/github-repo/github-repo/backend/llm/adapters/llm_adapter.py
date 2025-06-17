"""
Generic LLM Context Adapter - Works with any LLM provider (Gemini, Local, etc.)
"""

from typing import List, Dict, Any
import json
from datetime import datetime

class LLMContextAdapter:
    """Generic adapter to convert agent context to LLM-compatible format"""
    
    def to_llm_prompt(self, context: Dict[str, Any], provider_type: str = 'gemini') -> str:
        """
        Convert agent context to LLM prompt format
        
        Args:
            context: Agent context dictionary
            provider_type: Type of LLM provider ('gemini', 'local', etc.)
        
        Returns:
            Formatted prompt string
        """
        # Build system context
        system_lines = [
            f"You are {context.get('identity', {}).get('agent_id', 'FNTX Agent')}, "
            f"a {context.get('identity', {}).get('agent_type', 'trading')} agent for FNTX.ai.",
            f"Provider: {context.get('identity', {}).get('model_provider', provider_type)}",
            "",
            "System Context:",
            f"- Trading Session: {context.get('session_id', 'current')}",
            f"- Last Updated: {context.get('last_updated', datetime.now().isoformat())}",
            ""
        ]
        
        # Add goals if present
        if context.get('goals'):
            system_lines.append("Active Goals:")
            for goal in context['goals']:
                if goal.get('status') == 'active':
                    progress = (goal.get('current_value', 0) / goal.get('target_value', 1) * 100) if goal.get('target_value', 0) > 0 else 0
                    system_lines.append(
                        f"- [{goal.get('goal_type', 'unknown')}] {goal.get('goal_id', 'unnamed')}: "
                        f"{progress:.1f}% complete (Priority: {goal.get('priority', 50)})"
                    )
            system_lines.append("")
        
        # Add current plan status
        if context.get('plan'):
            plan = context['plan']
            system_lines.extend([
                f"Current Plan: {plan.get('plan_id', 'unknown')} (Status: {plan.get('status', 'unknown')})",
                f"Progress: Step {plan.get('current_step', 0)}/{len(plan.get('steps', []))}",
                ""
            ])
        
        # Add market state from shared context
        if context.get('shared_state'):
            system_lines.extend([
                "Market State:",
                f"- SPY Price: ${context['shared_state'].get('spy_price', 0):.2f}",
                f"- Market Open: {context['shared_state'].get('market_open', False)}",
                f"- VIX Level: {context['shared_state'].get('vix_level', 0):.2f}",
                f"- Market Regime: {context['shared_state'].get('market_regime', 'unknown')}",
                ""
            ])
        
        # Add constraints
        if context.get('identity', {}).get('constraints'):
            system_lines.extend([
                "Operating Constraints:",
                json.dumps(context['identity']['constraints'], indent=2),
                ""
            ])
        
        # Add recent memory context
        if context.get('memory'):
            system_lines.append("Recent Context:")
            recent_memories = sorted(
                context['memory'],
                key=lambda m: m.get('timestamp', datetime.min),
                reverse=True
            )[:5]  # Last 5 memories
            
            for memory in recent_memories:
                timestamp = memory.get('timestamp', '')
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        pass
                
                if isinstance(timestamp, datetime):
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
                else:
                    timestamp_str = str(timestamp)
                
                content_preview = self._format_memory_content(memory)
                system_lines.append(f"- [{memory.get('content_type', 'unknown').upper()} - {timestamp_str}] {content_preview}")
        
        return "\n".join(system_lines)
    
    def _format_memory_content(self, memory: Dict[str, Any]) -> str:
        """Format memory content for readability"""
        content = memory.get('content', {})
        content_type = memory.get('content_type', 'unknown')
        
        if content_type == 'trade':
            return (
                f"Trade: {content.get('action', 'UNKNOWN')} "
                f"{content.get('symbol', 'SPY')} {content.get('strike', 0)} "
                f"{content.get('option_type', 'PUT')} @ ${content.get('premium', 0):.2f}"
            )
        elif content_type == 'observation':
            return f"Observation: {content.get('observation', 'No details')}"
        elif content_type == 'decision':
            return f"Decision: {content.get('decision', 'No details')} (Confidence: {content.get('confidence', 0):.2f})"
        elif content_type == 'reflection':
            return f"Reflection: {content.get('insight', 'No details')}"
        else:
            # Generic format - show first few keys
            if isinstance(content, dict):
                preview_keys = list(content.keys())[:3]
                return f"{content_type}: {', '.join(preview_keys)}"
            else:
                return f"{content_type}: {str(content)[:100]}"
    
    def extract_structured_response(self, llm_response: str, expected_format: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from LLM response
        
        Args:
            llm_response: Raw response from LLM
            expected_format: Expected format/schema for extraction
        
        Returns:
            Structured dictionary with extracted data
        """
        # Try to find JSON in the response
        try:
            # Look for JSON blocks in the response
            import re
            json_pattern = r'\{[^{}]*\}'
            matches = re.findall(json_pattern, llm_response, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    # Validate against expected format if provided
                    if self._validate_format(data, expected_format):
                        return data
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        
        # Fallback: Parse key-value pairs
        extracted = {}
        for key in expected_format.keys():
            # Look for patterns like "key: value" or "key = value"
            patterns = [
                rf"{key}:\s*([^\n]+)",
                rf"{key}\s*=\s*([^\n]+)",
                rf'"{key}":\s*"([^"]+)"',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, llm_response, re.IGNORECASE)
                if match:
                    extracted[key] = match.group(1).strip()
                    break
        
        return extracted
    
    def _validate_format(self, data: Dict[str, Any], expected: Dict[str, Any]) -> bool:
        """Validate data matches expected format"""
        if not expected:
            return True
        
        # Check if all required keys are present
        for key in expected.keys():
            if key not in data:
                return False
        
        return True