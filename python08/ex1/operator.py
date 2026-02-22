#!/usr/bin/env python3
"""
operator.py
contains functions to get create show data and that
"""
import importlib


def check_dependency(pkg_name, import_name=None):
    """To import modules later and not on top"""
    import_name = import_name or pkg_name
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'Unknown')
        print(f"[OK] {pkg_name} ({version}) ready")
        return module
    except ImportError:
        print(f"[MISSING] {pkg_name} not " +
              "installed. Install with pip or Poetry!")
        return None


def generate_data(pd, np, n=1000):
    """Genera un DataFrame simulado"""
    data = pd.DataFrame({
        'matrix_x': np.random.randn(n),
        'matrix_y': np.random.randn(n)
    })
    print(f"Processing {n} data points...")
    return data


def load_silent(import_name):
    """Load a module silently without printing anything"""
    try:
        return importlib.import_module(import_name)
    except ImportError:
        return None


def visualize_data(plt, df, filename="matrix_analysis.png") -> None:
    """Visualize data"""
    plt.scatter(df['matrix_x'], df['matrix_y'], alpha=0.5)
    plt.title("Matrix Data Visualization")
    plt.xlabel("X values")
    plt.ylabel("Y values")
    plt.savefig(filename)
    print(f"Results saved to: {filename}")


def main() -> None:
    """
    python -m pip install poetry
    Main program
    run from dir above as operator is builtin
    python -m venv ex1/matrix_env
    source matrix_env/Scripts/activate
    python -m ex01.operator
    """
    print("OPERATOR STATUS: Loading programs...\n\nChecking dependencies:")

    pd = check_dependency("pandas")
    plt = check_dependency("matplotlib", "matplotlib.pyplot")
    requests = check_dependency("requests")
    np = load_silent("numpy")

    if not all([pd, np, plt, requests]):
        print("\nSome dependencies are missing. Install them with:")
        print("pip install -r requirements.txt")
        print("or use Poetry: poetry install")
        return

    print("\nAnalyzing Matrix data...")
    df = generate_data(pd, np, 1000)
    print("Generating visualization...")
    visualize_data(plt, df)
    print("Analysis complete!")


if __name__ == "__main__":
    main()
