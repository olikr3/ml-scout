# gpu_optimus/analyzer.py
import json
import os

# Load a simple cost database. You'll expand this later.
COST_DB = {
    "aws": {
        "p3.2xlarge": 3.06,
        "g5.12xlarge": 5.67,
        "g4dn.2xlarge": 1.20,
    },
    "azure": {
        "Standard_NC6s_v3": 1.80,
    },
    "gcp": {
        "n1-standard-16": 0.0, # Placeholder
    }
}

def load_cost_db():
    """Load the cost database from a JSON file."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cost_db_path = os.path.join(base_dir, 'cost_db.json')
        with open(cost_db_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: cost_db.json not found. Using default costs.")
        return COST_DB

def analyze_run(stats, instance_type="p3.2xlarge", cloud_provider="aws"):
    """Analyze the profiled data and generate recommendations."""
    cost_db = load_cost_db()
    hourly_rate = cost_db.get(cloud_provider, {}).get(instance_type, 0)

    # Calculate costs
    duration_hours = stats['duration_sec'] / 3600
    total_cost = hourly_rate * duration_hours
    wasted_cost = total_cost * (stats['idle_percent'] / 100)

    # Generate recommendations
    recommendations = []
    if stats['idle_percent'] > 20:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Idle Time',
            'message': f"GPU was idle {stats['idle_percent']:.1f}% of the time. This is often a CPU/data loading bottleneck.",
            'suggestion': "Try increasing `num_workers` in your DataLoader, using a faster storage solution, or using `webdataset` format."
        })

    if stats['peak_mem_util_gb'] < stats['mem_total_gb'] * 0.6:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Underutilized VRAM',
            'message': f"Peak GPU memory usage was {stats['peak_mem_util_gb']:.1f}GB out of {stats['mem_total_gb']:.1f}GB available.",
            'suggestion': "You can likely use a smaller, cheaper instance type or increase your batch size significantly."
        })
    elif stats['peak_mem_util_gb'] > stats['mem_total_gb'] * 0.95:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'VRAM Bottleneck',
            'message': "Peak GPU memory usage is dangerously close to the limit, risking Out-of-Memory (OOM) errors.",
            'suggestion': "You need a larger instance type, or must reduce your model size/batch size."
        })

    if stats['avg_compute_util'] < 50:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Low Compute',
            'message': f"Average GPU compute utilization was only {stats['avg_compute_util']:.1f}%.",
            'suggestion': "This can be caused by small model size, small batch size, or inefficient kernels. Try using `torch.compile` or increasing batch size."
        })

    return {
        'cost_analysis': {
            'instance_type': instance_type,
            'cloud_provider': cloud_provider,
            'hourly_rate': hourly_rate,
            'duration_hours': duration_hours,
            'total_cost': total_cost,
            'wasted_cost': wasted_cost,
        },
        'recommendations': recommendations
    }
