#!/usr/bin/env python3
"""
Example 3: Industrial Turbocharger Analysis

Demonstrates FeaGPT's capability for rotating machinery:
- 7-blade compressor at 110,000 RPM with cyclic symmetry
- 12-blade turbine with nickel superalloy
- Prestressed modal analysis (centrifugal + frequency extraction)

From FeaGPT paper Section III.G - Industrial Validation.
"""

from feagpt import GMSAPipeline, FeaGPTConfig


def run_compressor_analysis():
    """Analyze turbocharger compressor rotor."""
        config = FeaGPTConfig("config.yaml")
            pipeline = GMSAPipeline(config)

                description = (
                        "Analyze a 7-blade turbocharger compressor at 110,000 RPM. "
                                "Material: Aluminum C355 with E=75,000 MPa, nu=0.3, "
                                        "rho=2.65E-9 tonne/mm3. Apply cyclic symmetry with axis along "
                                                "X-direction. Perform static analysis with centrifugal loading, "
                                                        "then frequency analysis to find 6 natural modes using "
                                                                "Lanczos eigensolver."
                                                                    )

                                                                        result = pipeline.run(description)

                                                                            if result.success:
                                                                                    print("Compressor analysis completed successfully!")
                                                                                            print(f"  Max von Mises stress: {result.max_stress:.1f} MPa")
                                                                                                    print(f"  Max displacement: {result.max_displacement:.4f} mm")
                                                                                                            if result.frequencies:
                                                                                                                        print(f"  Natural frequencies: {result.frequencies}")
                                                                                                                            else:
                                                                                                                                    print(f"Analysis failed: {result.error}")


                                                                                                                                    def run_turbine_analysis():
                                                                                                                                        """Analyze turbocharger turbine rotor."""
                                                                                                                                            config = FeaGPTConfig("config.yaml")
                                                                                                                                                pipeline = GMSAPipeline(config)

                                                                                                                                                    description = (
                                                                                                                                                                "Analyze a 12-blade turbocharger turbine at 110,000 RPM. "
                                                                                                                                                                        "Material: Nickel superalloy Inconel 718 with E=200,000 MPa, "
                                                                                                                                                                                "nu=0.3, rho=8.19E-9 tonne/mm3. Apply cyclic symmetry with "
                                                                                                                                                                                        "N=12 sectors. Perform centrifugal static analysis followed by "
                                                                                                                                                                                                "modal analysis to extract 6 natural frequencies."
                                                                                                                                                                                                    )

                                                                                                                                                                                                        result = pipeline.run(description)

                                                                                                                                                                                                            if result.success:
                                                                                                                                                                                                                        print("Turbine analysis completed successfully!")
                                                                                                                                                                                                                                print(f"  Max von Mises stress: {result.max_stress:.1f} MPa")
                                                                                                                                                                                                                                        print(f"  Max displacement: {result.max_displacement:.4f} mm")
                                                                                                                                                                                                                                            else:
                                                                                                                                                                                                                                                        print(f"Analysis failed: {result.error}")


                                                                                                                                                                                                                                                        if __name__ == "__main__":
                                                                                                                                                                                                                                                                print("=" * 60)
                                                                                                                                                                                                                                                                    print("FeaGPT - Turbocharger Analysis")
                                                                                                                                                                                                                                                                        print("=" * 60)

                                                                                                                                                                                                                                                                            print("\n--- Compressor (7-blade, Al C355) ---")
                                                                                                                                                                                                                                                                                run_compressor_analysis()

                                                                                                                                                                                                                                                                                    print("\n--- Turbine (12-blade, Inconel 718) ---")
                                                                                                                                                                                                                                                                                        run_turbine_analysis()
                                                                                                                                                    )