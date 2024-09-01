from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
from pathlib import Path
from datetime import datetime
import geopandas as gpd # type: ignore
from shapely.geometry import Point # type: ignore

sys.path.append(str(Path(__file__).resolve().parent))
from utils.data_utils import DataAcquisitionProcessor, DataPreProcessor, DataCleanupProcessor # type: ignore  
from utils.model_utils import ModelSetupInitializer # type: ignore
from utils.optimization_utils import OptimizationCalibrator # type: ignore
from utils.reporting_utils import VisualizationReporter # type: ignore
from utils.workflow_utils import WorkflowManager # type: ignore
from utils.forecasting_utils import ForecastingEngine # type: ignore
from utils.uncertainty_utils import UncertaintyQuantifier # type:ignore
from utils.logging_utils import setup_logger, get_function_logger # type: ignore
from utils.config_utils import ConfigManager # type: ignore
from utils.geofabric_utils import GeofabricSubsetter, GeofabricDelineator, LumpedWatershedDelineator # type: ignore
from utils.discretization_utils import DomainDiscretizer # type: ignore


class CONFLUENCE:

    """
    CONFLUENCE: Community Optimization and Numerical Framework for Large-domain Understanding of 
    Environmental Networks and Computational Exploration

    This class serves as the main interface for the CONFLUENCE hydrological modeling platform. 
    It integrates various components for data management, model setup, optimization, 
    uncertainty analysis, forecasting, visualization, and workflow management.

    The platform is designed to facilitate comprehensive hydrological modeling and analysis
    across various scales and regions, supporting multiple models and analysis techniques.

    Attributes:
        config (Dict[str, Any]): Configuration settings for the CONFLUENCE system
        logger (logging.Logger): Logger for the CONFLUENCE system
        data_manager (DataAcquisitionProcessor): Handles data acquisition and processing
        model_manager (ModelSetupInitializer): Manages model setup and initialization
        optimizer (OptimizationCalibrator): Handles model optimization and calibration
        uncertainty_analyzer (UncertaintyQuantifier): Performs uncertainty analysis
        forecaster (ForecastingEngine): Generates hydrological forecasts
        visualizer (VisualizationReporter): Creates visualizations and reports
        workflow_manager (WorkflowManager): Manages modeling workflows

    """

    def __init__(self, config):
        """
        Initialize the CONFLUENCE system.

        Args:
            config (Config): Configuration object containing optimization settings for the CONFLUENCE system
        """
        self.config_manager = ConfigManager(config)
        self.config = self.config_manager.config
        self.data_dir = Path(self.config.get('CONFLUENCE_DATA_DIR'))
        self.domain_name = self.config.get('DOMAIN_NAME')
        self.project_dir = self.data_dir / f"domain_{self.domain_name}"

        self.setup_logging()

    def setup_logging(self):
        log_dir = self.data_dir / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f'confluence_general_{self.domain_name}_{current_time}.log'
        self.logger = setup_logger('confluence_general', log_file)

    @get_function_logger
    def setup_project(self):
        self.logger.info(f"Setting up project for domain: {self.domain_name}")

        # Create project directory and 
        self.project_dir = self.data_dir / f"domain_{self.domain_name}"
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Log to both the general logger and the function-specific logger
        self.logger.info(f"Project directory created at: {self.project_dir}")
        logger.info(f"Project directory created at: {self.project_dir}")

        # Create shapefile directory and required sub-directories
        shapefile_dir = self.project_dir / f"shapefiles"
        shapefile_dir.mkdir(parents=True, exist_ok=True)
        pourPoint_dir = shapefile_dir / f"pour_point"
        pourPoint_dir.mkdir(parents=True, exist_ok=True)
        catchment_dir = shapefile_dir / f"catchment"
        catchment_dir.mkdir(parents=True, exist_ok=True)
        riverNetwork_dir = shapefile_dir / f"river_network"
        riverNetwork_dir.mkdir(parents=True, exist_ok=True)
        riverBasins_dir = shapefile_dir / f"river_basins"
        riverBasins_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"shapefiles directories created at {shapefile_dir},\n {pourPoint_dir},\n {catchment_dir},\n {riverNetwork_dir},\n {riverBasins_dir}")
        self.logger.info(f"shapefiles directories created at {shapefile_dir},\n {pourPoint_dir},\n {catchment_dir},\n {riverNetwork_dir},\n {riverBasins_dir}")
        
        return self.project_dir

    @get_function_logger
    def create_pourPoint(self):

        if self.config.get('POUR_POINT_COORDS', 'default').lower() == 'default':
            self.logger.info("Using user-provided pour point shapefile")
            return None
        
        try:
            lat, lon = map(float, self.config['POUR_POINT_COORDS'].split('/'))
            point = Point(lon, lat)
            gdf = gpd.GeoDataFrame({'geometry': [point]}, crs="EPSG:4326")
            
            if self.config.get('POUR_POINT_SHP_PATH') == 'default':
                output_path = self.project_dir / "shapefiles" / "pour_point"
            else:
                output_path = Path(self.config['POUR_POINT_SHP_PATH'])
            
            self.logger.info(f"Creating pour point shapefile in {output_path}")
            logger.info(f"Creating pour point shapefile in {output_path}")

            pour_point_shp_name = self.config.get('POUR_POINT_SHP_NAME')
            if pour_point_shp_name == 'default':
                pour_point_shp_name = f"{self.domain_name}_pourPoint.shp"
            
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / pour_point_shp_name
            
            gdf.to_file(output_file)
            self.logger.info(f"Pour point shapefile created successfully: {output_file}")
            return output_file
        except ValueError:
            self.logger.error("Invalid pour point coordinates format. Expected 'lat/lon'.")
        except Exception as e:
            self.logger.error(f"Error creating pour point shapefile: {str(e)}")
        
        return None

    @get_function_logger
    def define_domain(self):
        domain_method = self.config.get('DOMAIN_DEFINITION_METHOD')
        
        if domain_method == 'subset_geofabric':
            self.subset_geofabric(work_log_dir=self.data_dir / f"domain_{self.domain_name}" / f"shapefiles/_workLog")
        elif domain_method == 'lumped_watershed':
            self.delineate_lumped_watershed(work_log_dir=self.data_dir / f"domain_{self.domain_name}" / f"shapefiles/_workLog")
        elif domain_method == 'delineate_geofabric':
            self.delineate_geofabric(work_log_dir=self.data_dir / f"domain_{self.domain_name}" / f"shapefiles/_workLog")
        else:
            self.logger.error(f"Unknown domain definition method: {domain_method}")

        domain_discretizer = DomainDiscretizer(self.config, self.logger)
        hru_shapefile = domain_discretizer.discretize_domain()
        if hru_shapefile:
            self.logger.info(f"Domain discretized successfully. HRU shapefile: {hru_shapefile}")
        else:
            self.logger.error("Domain discretization failed.")

        logger.info(f"Domain to be defined using method {domain_method}")


    @get_function_logger
    def subset_geofabric(self):
        self.logger.info("Starting geofabric subsetting process")
        
        # Ensure all required config keys are present
        required_keys = ['GEOFABRIC_TYPE', 'SOURCE_GEOFABRIC_BASINS_PATH', 'SOURCE_GEOFABRIC_RIVERS_PATH',
                         'POUR_POINT_SHP_PATH', 'OUTPUT_BASINS_PATH', 'OUTPUT_RIVERS_PATH']
        
        for key in required_keys:
            if key not in self.config:
                self.logger.error(f"Missing required configuration key: {key}")
                return None

        # Create GeofabricSubsetter instance
        subsetter = GeofabricSubsetter(self.config, self.logger)
        
        try:
            subset_basins, subset_rivers = subsetter.subset_geofabric()
            self.logger.info("Geofabric subsetting completed successfully")
            return subset_basins, subset_rivers
        except Exception as e:
            self.logger.error(f"Error during geofabric subsetting: {str(e)}")
            return None

    @get_function_logger
    def delineate_lumped_watershed(self):
        self.logger.info("Starting geofabric lumped delineation")
        try:
            delineator = LumpedWatershedDelineator(self.config, self.logger)
            self.logger.info('Geofabric delineation completed successfully')
            return delineator.delineate_lumped_watershed()
        except Exception as e:
            self.logger.error(f"Error during geofabric delineation: {str(e)}")
            return None

    @get_function_logger
    def delineate_geofabric(self):
        self.logger.info("Starting geofabric delineation")
        try:
            delineator = GeofabricDelineator(self.config, self.logger)
            self.logger.info('Geofabric delineation completed successfully')
            return delineator.delineate_geofabric()
        except Exception as e:
            self.logger.error(f"Error during geofabric delineation: {str(e)}")
            return None

    @get_function_logger
    def process_input_data(self):
        self.logger.info("Starting input data processing")
        
        # Create DataAcquisitionProcessor instance
        data_acquisition = DataAcquisitionProcessor(self.config, self.logger)
        
        # Run data acquisition
        try:
            data_acquisition.run_data_acquisition()
        except Exception as e:
            self.logger.error(f"Error during data acquisition: {str(e)}")
            raise
        
        # Create DataCleanupProcessor instance
        data_cleanup = DataCleanupProcessor(self.config, self.logger)
        
        # Run data cleanup and checks
        try:
            data_cleanup.cleanup_and_checks()
        except Exception as e:
            self.logger.error(f"Error during data cleanup: {str(e)}")
            raise
        
        self.logger.info("Input data processing completed")

    def load_project(self, project_name):
        # Load an existing project
        pass

    def setup_model(self, model_type, spatial_resolution, temporal_resolution):
        # Set up a hydrological model with specified parameters
        pass

    def calibrate_model(self, calibration_method, objective_function, constraints):
        # Calibrate the model using specified method and objectives
        pass

    def run_sensitivity_analysis(self, method, parameters):
        # Perform sensitivity analysis on model parameters
        pass

    def quantify_uncertainty(self, method, parameters):
        # Quantify uncertainty in model outputs
        pass

    def generate_forecast(self, forecast_horizon, ensemble_size):
        # Generate hydrological forecasts
        pass

    def analyze_results(self, analysis_type, metrics):
        # Analyze model outputs and forecasts
        pass

    def visualize_results(self, visualization_type, output_format):
        # Create visualizations of results
        pass

    def export_results(self, format, destination):
        # Export results in specified format
        pass

    @get_function_logger
    def run_workflow(self):
        self.logger.info("Starting CONFLUENCE workflow")
        
        # Check if we should force run all steps
        force_run = self.config.get('FORCE_RUN_ALL_STEPS', False)
        
        # Define the workflow steps and their output checks
        workflow_steps = [
            (self.setup_project, self.project_dir.exists),
            (self.create_pourPoint, lambda: (self.project_dir / "shapefiles" / "pour_point" / f"{self.domain_name}_pourPoint.shp").exists()),
            (self.define_domain, lambda: (self.project_dir / "shapefiles" / "river_basins" / f"{self.domain_name}_riverBasins_delineated.shp").exists()),
            (self.process_input_data, lambda: (self.project_dir / "parameters" / "dem" / "modified_domain_stats_elv.csv").exists())
        ]
        
        for step_func, check_func in workflow_steps:
            step_name = step_func.__name__
            if force_run or not check_func():
                self.logger.info(f"Running step: {step_name}")
                try:
                    step_func()
                except Exception as e:
                    self.logger.error(f"Error during {step_name}: {str(e)}")
                    raise
            else:
                self.logger.info(f"Skipping step {step_name} as output already exists")
        
        self.logger.info("CONFLUENCE workflow completed")

def main():
    config_path = Path(__file__).parent / '0_config_files'
    config_name = 'config_active.yaml'

    confluence = CONFLUENCE(config_path / config_name)
    confluence.run_workflow()
    
if __name__ == "__main__":
    main()