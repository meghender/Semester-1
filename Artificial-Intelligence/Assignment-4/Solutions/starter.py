import re

def parse_bif(filename):
    """Extract Bayesian network structure from BIF format"""
    with open(filename, 'r') as file_handle:
        file_content = file_handle.read()
    
    network_structure = {}
    
    # Extract variable definitions first to maintain order
    variable_regex = re.compile(
        r'variable\s+(\w+)\s*\{\s*type\s+discrete\s*\[\s*\d+\s*\]\s*=\s*\{\s*([^\}]+)\s*\}\s*;',
        re.MULTILINE
    )

    for var_name, domain_str in variable_regex.findall(file_content):
        # Clean up domain values - handle quotes and commas
        domain_values = []
        for val in re.split(r'[,\s]+', domain_str):
            val = val.strip().strip('"').strip("'")
            if val:
                domain_values.append(val)
        
        network_structure[var_name] = {
            "values": domain_values,
            "parents": [],
            "probabilities": {}
        }
    
    # Extract probability distributions
    probability_regex = re.compile(
        r'probability\s*\(\s*([^\|\)]+?)\s*(?:\|\s*([^\)]+))?\s*\)\s*\{(.*?)\};',
        re.DOTALL | re.MULTILINE
    )

    for node, parent_list_str, distribution_body in probability_regex.findall(file_content):
        node = node.strip()
        parent_nodes = [p.strip() for p in parent_list_str.split(',')] if parent_list_str else []

        if node in network_structure:
            network_structure[node]["parents"] = parent_nodes
        else:
            # This shouldn't happen but handle it gracefully
            network_structure[node] = {
                "values": [], 
                "parents": parent_nodes, 
                "probabilities": {}
            }

        # Parse distribution body
        distribution_body = distribution_body.strip()
        if distribution_body.startswith("table"):
            # Unconditional probability table - use "()" as key for consistency
            numeric_values = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?|-1', distribution_body)
            probability_vector = [float(v) if v != '-1' else -1 for v in numeric_values]
            # Use string "()" as key, not tuple, for format checker compatibility
            network_structure[node]["probabilities"]["()"] = probability_vector
        else:
            # Conditional probability table
            conditional_pattern = re.compile(r'\(([^\)]+)\)\s*([^;\(]+)')
            for parent_config, prob_str in conditional_pattern.findall(distribution_body):
                # Clean up parent configuration
                config_values = []
                for v in parent_config.split(','):
                    v = v.strip().strip('"').strip("'")
                    if v:
                        config_values.append(v)
                config_key = tuple(config_values)
                
                # Extract probabilities
                numeric_values = re.findall(r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?|-1', prob_str)
                probability_vector = [float(x) if x != '-1' else -1 for x in numeric_values]
                network_structure[node]["probabilities"][config_key] = probability_vector

    return network_structure
