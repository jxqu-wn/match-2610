"""Token statistics distinguish service usage from local tokenizer estimates."""
import json
import math
from statistics import mean

from context import token_upper_bound


def context_profile(context, system, tokenizer):
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False, separators=(',', ':'))}]
    return {'utf8_upper_bound': token_upper_bound(messages),
            'local_proxy_input_tokens': sum(len(tokenizer.encode(m['content'])) + 8 for m in messages) + 8,
            'proxy_tokenizer': 'local Qwen embedding tokenizer; NOT exact DeepSeek usage',
            'tables': len(context['candidate_tables']),
            'columns': sum(len(t['columns']) for t in context['candidate_tables']),
            'knowledge': len(context['knowledge']), 'examples': len(context['examples'])}


def distribution(values):
    values = sorted(values)
    if not values:
        return {'count': 0}
    def quantile(p):
        return values[max(0, math.ceil(p * len(values)) - 1)]
    return {'count': len(values), 'mean': mean(values), 'p50': quantile(.5),
            'p90': quantile(.9), 'p95': quantile(.95), 'max': max(values)}


def summarize_tokens(cases):
    calls = [c for case in cases for c in case['execution']['transport_calls'] if c.get('success')]
    prompts = [c['usage']['prompt_tokens'] for c in calls if 'prompt_tokens' in c.get('usage', {})]
    completions = [c['usage']['completion_tokens'] for c in calls if 'completion_tokens' in c.get('usage', {})]
    ratios, raw_estimates = [], []
    for case in cases:
        first = next((c for c in case['execution']['transport_calls'] if c.get('success') and c['purpose'] == 'judgment'), None)
        profile = case.get('context_profiles', {})
        if first and first.get('usage', {}).get('prompt_tokens') and profile.get('raw') and profile.get('fitted') and profile['fitted'].get('stage') != 'business_database':
            fitted = profile['fitted']['local_proxy_input_tokens']
            ratio = first['usage']['prompt_tokens'] / max(fitted, 1)
            ratios.append(ratio)
            raw_estimates.append(math.ceil(profile['raw']['local_proxy_input_tokens'] * ratio))
    return {'actual_input_tokens': distribution(prompts), 'actual_output_tokens': distribution(completions),
            'by_purpose': {purpose: {'calls': sum(c.get('purpose') == purpose for c in calls),
                                     'input_tokens': sum(c.get('usage', {}).get('prompt_tokens', 0) for c in calls if c.get('purpose') == purpose),
                                     'output_tokens': sum(c.get('usage', {}).get('completion_tokens', 0) for c in calls if c.get('purpose') == purpose)}
                           for purpose in sorted({c.get('purpose', 'unknown') for c in calls})},
            'actual_total_tokens': distribution([c['usage']['total_tokens'] for c in calls if 'total_tokens' in c.get('usage', {})]),
            'actual_input_per_local_proxy_token': distribution(ratios),
            'uncropped_input_estimates': distribution(raw_estimates),
            'uncropped_estimate_note': 'Per-question ratio calibrated on its first real prompt; uncropped inputs were NOT measured by the service.',
            'output_length_stops': sum(c.get('finish_reason') == 'length' for c in calls),
            'cache_hit_tokens': sum(c.get('usage', {}).get('prompt_cache_hit_tokens', 0) for c in calls),
            'cache_miss_tokens': sum(c.get('usage', {}).get('prompt_cache_miss_tokens', 0) for c in calls),
            'recommendation_status': 'Use observed quantiles plus headroom; A sampled pilot is not a production guarantee.'}
