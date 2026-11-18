# AMIGO TIB Feature Extraction Contract
# Maps raw TIB bar data to strategy-consumable feature vectors.

# 1. RAW TIB BAR (Source: tib_generator.py)
# - open, high, low, close, tick_count, imbalance, threshold, timestamp

# 2. EXTRACTED FEATURES (Target: Python/tib_feature_contract.py)
# - ImbalanceIntensity: (imbalance / tick_count)
# - VolatilityProxy: (high - low) / tick_count
# - DirectionalPersistence: sign(imbalance)
# - BarActivity: tick_count (relative to moving average)

def extract_features(tib_bar):
    features = {
        'timestamp': tib_bar['timestamp'],
        'imb_intensity': tib_bar['imbalance'] / tib_bar['tick_count'] if tib_bar['tick_count'] > 0 else 0,
        'vol_proxy': (tib_bar['high'] - tib_bar['low']) / tib_bar['tick_count'] if tib_bar['tick_count'] > 0 else 0,
        'dir_persistence': 1 if tib_bar['imbalance'] > 0 else (-1 if tib_bar['imbalance'] < 0 else 0),
        'bar_activity': tib_bar['tick_count']
    }
    return features

# Integration point: Shared Market Context
# These features feed the Regime Engine and Strategy Analysis modules.
