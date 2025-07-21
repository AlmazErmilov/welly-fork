"""
Welly MCP Tools

Implements MCP (Model Context Protocol) tools for petrophysical analysis using welly.
These tools enable AI assistants to perform well log analysis through natural language.
"""

import base64
import io
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Import welly components
from welly import Well, Project
import lasio

from .session import SessionManager

logger = logging.getLogger(__name__)

class WellyMCPTools:
    """MCP tools for welly petrophysical analysis."""
    
    def __init__(self, session_manager: SessionManager):
        """Initialize with session manager."""
        self.session_manager = session_manager
    
    def _extract_depth_info(self, well):
        """Extract depth information from well curves."""
        try:
            if not well.data:
                return {'start': None, 'stop': None, 'step': None}
            
            # Use curve properties for depth information
            first_curve = list(well.data.values())[0]
            
            return {
                'start': first_curve.start,
                'stop': first_curve.stop,
                'step': first_curve.step
            }
            
        except Exception:
            return {'start': None, 'stop': None, 'step': None}
    
    async def load_las_well(self, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Load a LAS file and create a Well object.
        
        Args:
            args: Dictionary containing:
                - file_path: Absolute or relative path to a LAS file on disk (e.g., "/path/to/well.las")
                  NOTE: This must be a file path, not file contents. The file must exist on the filesystem.
                - alias_dict: Optional dictionary to rename curves (e.g., {"GR": "GAMMA_RAY", "DEPT": "DEPTH"})
            session_id: Session identifier
            
        Returns:
            Dictionary containing:
                - well_id: Unique identifier for the loaded well (use this for subsequent operations)
                - curves: List of curve names available in the well
                - metadata: Well information including name, location, depth range
                - message: Success message
                
        Example:
            args = {
                "file_path": "/data/wells/example.las",
                "alias_dict": {"GR": "GAMMA_RAY"}  # optional
            }
        """
        try:
            file_path = args['file_path']
            alias_dict = args.get('alias_dict', {})
            
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"LAS file not found: {file_path}")
            
            if not file_path.lower().endswith('.las'):
                raise ValueError("File must be a LAS file (.las extension)")
            
            # Load LAS file using welly
            well = Well.from_las(file_path, alias=alias_dict)
            
            # Generate unique well ID
            well_id = str(uuid.uuid4())
            
            # Store in session
            self.session_manager.store_well(session_id, well_id, well)
            
            # Get curve information
            curves = list(well.data.keys()) if well.data else []
            
            # Extract basic metadata (handle different welly API versions)
            metadata = {
                'well_name': getattr(well, 'name', 'Unknown'),
                'location': {
                    'x': getattr(well.location, 'x', None) if hasattr(well, 'location') and well.location else None,
                    'y': getattr(well.location, 'y', None) if hasattr(well, 'location') and well.location else None
                },
                'start_depth': None,
                'stop_depth': None, 
                'step_size': None,
                'total_curves': len(curves)
            }
            
            # Extract depth information
            depth_info = self._extract_depth_info(well)
            metadata.update({
                'start_depth': depth_info['start'],
                'stop_depth': depth_info['stop'],
                'step_size': depth_info['step']
            })
            
            result = {
                'well_id': well_id,
                'curves': curves,
                'metadata': metadata,
                'message': f"Successfully loaded LAS file: {Path(file_path).name}"
            }
            
            logger.info(f"Loaded well {well_id} with {len(curves)} curves")
            return result
            
        except Exception as e:
            logger.error(f"Failed to load LAS file: {e}")
            raise Exception(f"Error loading LAS file: {str(e)}")
    
    async def get_curve_stats(self, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Calculate statistical summary for well curves.
        
        Args:
            args: Dictionary containing:
                - well_id: ID of loaded well
                - curve_names: Optional list of curves to analyze
            session_id: Session identifier
            
        Returns:
            Dictionary with statistical analysis results
        """
        try:
            well_id = args['well_id']
            curve_names = args.get('curve_names', None)
            
            # Retrieve well from session
            well = self.session_manager.get_well(session_id, well_id)
            if well is None:
                raise ValueError(f"Well {well_id} not found in session {session_id}")
            
            # Determine curves to analyze
            if curve_names is None:
                curve_names = list(well.data.keys())
            else:
                # Validate requested curves exist
                available_curves = list(well.data.keys())
                invalid_curves = [c for c in curve_names if c not in available_curves]
                if invalid_curves:
                    raise ValueError(f"Curves not found: {invalid_curves}. Available: {available_curves}")
            
            stats_result = {}
            
            for curve_name in curve_names:
                curve = well.data[curve_name]
                
                try:
                    # Get curve statistics
                    stats_df = curve.describe()
                    curve_stats = stats_df[curve_name].to_dict()
                    
                    # Convert to our expected format with additional metadata
                    stats = {
                        'count': int(curve_stats['count']),
                        'mean': float(curve_stats['mean']),
                        'std': float(curve_stats['std']),
                        'min': float(curve_stats['min']),
                        'max': float(curve_stats['max']),
                        'median': float(curve_stats['50%']),  # median is 50th percentile
                        'percentile_25': float(curve_stats['25%']),
                        'percentile_75': float(curve_stats['75%']),
                        'null_count': len(curve.values) - int(curve_stats['count']),
                        'unit': getattr(curve, 'units', 'unknown')
                    }
                    
                except Exception:
                    # Fallback to basic statistics
                    basic_stats = curve.get_stats()
                    stats = {
                        'count': basic_stats.get('samples', 0),
                        'mean': basic_stats.get('mean', None),
                        'min': basic_stats.get('min', None),
                        'max': basic_stats.get('max', None),
                        'null_count': basic_stats.get('nulls', 0),
                        'unit': getattr(curve, 'units', 'unknown'),
                        'message': 'Limited statistics available'
                    }
                
                stats_result[curve_name] = stats
            
            result = {
                'well_id': well_id,
                'statistics': stats_result,
                'analyzed_curves': curve_names,
                'message': f"Statistical analysis completed for {len(curve_names)} curves"
            }
            
            logger.info(f"Calculated statistics for {len(curve_names)} curves in well {well_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to calculate curve statistics: {e}")
            raise Exception(f"Error calculating statistics: {str(e)}")
    
    async def plot_well_log(self, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Generate a well log plot visualization.
        
        Args:
            args: Dictionary containing:
                - well_id: ID of loaded well
                - curves: Optional list of curves to plot
                - depth_range: Optional [start, end] depth range
            session_id: Session identifier
            
        Returns:
            Dictionary with base64 encoded plot image
        """
        try:
            well_id = args['well_id']
            curve_names = args.get('curves', None)
            depth_range = args.get('depth_range', None)
            
            # Retrieve well from session
            well = self.session_manager.get_well(session_id, well_id)
            if well is None:
                raise ValueError(f"Well {well_id} not found in session {session_id}")
            
            # Determine curves to plot
            if curve_names is None:
                curve_names = list(well.data.keys())
                # Limit to first 6 curves for readability
                curve_names = curve_names[:6]
            
            # Validate curves exist
            available_curves = list(well.data.keys())
            invalid_curves = [c for c in curve_names if c not in available_curves]
            if invalid_curves:
                raise ValueError(f"Curves not found: {invalid_curves}. Available: {available_curves}")
            
            # Prepare tracks for welly plotting
            # Add depth track at the beginning for reference
            tracks = ['MD'] + curve_names
            
            # Apply depth filtering to well if specified
            plotting_well = well
            if depth_range and len(depth_range) == 2:
                start_depth, end_depth = depth_range
                # Create a copy of the well with limited depth range
                plotting_well = well  # Use original well, welly will handle extents
                extents = (start_depth, end_depth)
            else:
                extents = None
            
            # Generate plot using welly
            fig = plotting_well.plot(
                tracks=tracks,
                extents=extents,
                return_fig=True,
                figsize=(max(12, len(curve_names) * 2), 10)
            )
            
            # Convert plot to base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plot_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close(fig)
            
            result = {
                'well_id': well_id,
                'plot_base64': plot_base64,
                'plotted_curves': curve_names,
                'depth_range': depth_range,
                'message': f"Generated well log plot with {len(curve_names)} curves"
            }
            
            logger.info(f"Generated plot for well {well_id} with curves: {curve_names}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate plot: {e}")
            raise Exception(f"Error generating plot: {str(e)}")
    
    async def get_well_info(self, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Get header information and metadata from a well.
        
        Args:
            args: Dictionary containing:
                - well_id: ID of loaded well
            session_id: Session identifier
            
        Returns:
            Dictionary with well header and metadata information
        """
        try:
            well_id = args['well_id']
            
            # Retrieve well from session
            well = self.session_manager.get_well(session_id, well_id)
            if well is None:
                raise ValueError(f"Well {well_id} not found in session {session_id}")
            
            # Extract header information
            header_info = {}
            if hasattr(well, 'header') and well.header is not None:
                try:
                    # Handle DataFrame header
                    if hasattr(well.header, 'to_dict'):
                        header_info = well.header.to_dict()
                    else:
                        # Handle dict-like header
                        for section, data in well.header.items():
                            if isinstance(data, dict):
                                header_info[section] = dict(data)
                            else:
                                header_info[section] = str(data)
                except Exception:
                    header_info = {'error': 'Could not parse header information'}
            
            # Get curve information
            curves_info = {}
            if well.data:
                for curve_name, curve in well.data.items():
                    curves_info[curve_name] = {
                        'units': getattr(curve, 'units', 'unknown'),
                        'description': getattr(curve, 'description', ''),
                        'data_points': len(curve.values) if hasattr(curve, 'values') else len(curve)
                    }
            
            # Location information
            location_info = {}
            if hasattr(well, 'location') and well.location is not None:
                location_info = {
                    'x': getattr(well.location, 'x', None),
                    'y': getattr(well.location, 'y', None),
                    'kb': getattr(well.location, 'kb', None),
                    'crs': str(getattr(well.location, 'crs', 'unknown'))
                }
            
            result = {
                'well_id': well_id,
                'header': header_info,
                'curves': curves_info,
                'location': location_info,
                'depth_info': self._extract_depth_info(well),
                'message': f"Retrieved information for well {well_id}"
            }
            
            logger.info(f"Retrieved info for well {well_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get well info: {e}")
            raise Exception(f"Error getting well info: {str(e)}")
    
    async def list_curves(self, args: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        List all available curves in a well.
        
        Args:
            args: Dictionary containing:
                - well_id: ID of loaded well
            session_id: Session identifier
            
        Returns:
            Dictionary with list of available curves
        """
        try:
            well_id = args['well_id']
            
            # Retrieve well from session
            well = self.session_manager.get_well(session_id, well_id)
            if well is None:
                raise ValueError(f"Well {well_id} not found in session {session_id}")
            
            # Get curve names and details
            curves = []
            if well.data:
                for curve_name, curve in well.data.items():
                    curve_info = {
                        'name': curve_name,
                        'units': getattr(curve, 'units', 'unknown'),
                        'description': getattr(curve, 'description', ''),
                        'data_points': len(curve.values) if hasattr(curve, 'values') else len(curve),
                        'has_nulls': np.isnan(curve.values).any() if hasattr(curve, 'values') else False
                    }
                    curves.append(curve_info)
            
            result = {
                'well_id': well_id,
                'curves': curves,
                'total_curves': len(curves),
                'message': f"Found {len(curves)} curves in well {well_id}"
            }
            
            logger.info(f"Listed {len(curves)} curves for well {well_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list curves: {e}")
            raise Exception(f"Error listing curves: {str(e)}")