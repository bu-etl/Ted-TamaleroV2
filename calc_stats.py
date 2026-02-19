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

    sub_mean2 = np.array([x-combined_mean for x in means]) ** 2
    sqr_stds = np.array(stds) ** 2
    combined_varience : float = ( (pixels-1)/(pixels*n - 1) )*sum(sqr_stds)  +  ( pixels/(pixels*n - 1) )* sum(sub_mean2)

    combined_std : float = combined_varience ** 0.5
    
    sample_std : float = np.mean(stds)

    print(
    	f"Combined mean: {combined_mean}\n"
    	f"Combined stds: {combined_std}\n"
    	f"Sample stds: {sample_std}\n"
    )

if __name__ == "__main__":
    main()