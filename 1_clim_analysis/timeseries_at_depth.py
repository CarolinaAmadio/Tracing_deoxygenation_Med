def collect_data_from_profiles(profiles):
    """Collects data from profiles applying densities and masks."""
    def apply_density_mask(data, density_method):
        # Apply sophisticated mask checking and fallback logic for the specified method
        if density_method == 'rho_gsw':
            # Apply logic for rho_gsw
            pass
        elif density_method == 'rho_gsw_ins':
            # Apply logic for rho_gsw_ins
            pass
        elif density_method == 'rho_sw':
            # Apply logic for rho_sw
            pass
        elif density_method == 'rho_levant':
            # Apply logic for rho_levant
            pass
        return data

    # Main logic to collect and apply density
    for profile in profiles:
        profile['masked_data'] = apply_density_mask(profile['data'], profile['density_method'])
    return profiles

COLUMNS = ['depth', 'value_rho_gsw', 'value_rho_gsw_ins', 'value_rho_sw', 'value_rho_levant']
