def get_full_production_boost(handicap=0):
    """
    Assuming 3 production buildings, full power. Get the boost according to handicap
    :param handicap:
    :return:
    """
    handi_boost = [125, 100, 75]
    num_fac_boost = [100, 150, 200]

    return handi_boost[handicap] * num_fac_boost[2] // 100
