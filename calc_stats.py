import argparse

import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--means", type=float, nargs='+', required=True, help="Array of noisewidth means")
    ap.add_argument("--stds", type=float, nargs='+', required=True, help="Array of noisewidth standard deviations")
    ap.add_argument("--size", type=float, default=256.0, help="Number of pixels in noise scan (aka sample size per mean)")

    args = ap.parse_args()

    means: list[float] = args.means
    stds: list[float] = args.stds
    pixels: float = args.size
    n: float = len(means)

    if n != len(stds):
    	raise ValueError(
        f"Length mismatch: means has {len(means)} elements "
        f"but stds has {len(stds)} elements"
    	)

    combined_mean = np.mean(means)
    combined_varience : float = ( (pixels-1)*(sum(stds)**2)+ ((pixels**n) /(pixels *n))*( (means[0] - sum(means[1:])) ** 2 ) )   /   ( (pixels * n) - 1 )
    combined_std : float = combined_varience ** 0.5

if __name__ == "__main__":
    main()