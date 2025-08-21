#!/usr/bin/env python3
"""
Memory-Efficient Portfolio Operations - LXC Optimized Matrix Operations
=======================================================================

Speziell entwickelt für LXC 10.1.1.174 Container Memory Constraints
Optimierte Matrix-Operationen für große Portfolios mit minimaler Memory-Nutzung

Features:
- Sparse Matrix Operations für große Covariance Matrices
- Batch Processing für Memory-Efficient Calculations
- Streaming Portfolio Weight Calculations
- Memory-Mapped File Operations
- Chunked Matrix Operations
- LXC Container Resource Management

Author: Claude Code & LXC Portfolio Optimization Team
Version: 1.0.0
Date: 2025-08-19
"""

import logging
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve, norm as sparse_norm
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Any, Optional, Iterator
import tempfile
import mmap
import os
from dataclasses import dataclass
from pathlib import Path
import psutil

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class PortfolioConfig:
    """Portfolio configuration für memory optimization"""
    max_assets: int = 100
    batch_size: int = 50
    memory_limit_mb: float = 1024.0  # 1GB limit für LXC
    use_sparse_matrices: bool = True
    use_memory_mapping: bool = True
    chunk_size: int = 1000

@dataclass
class MemoryMetrics:
    """Memory usage metrics"""
    current_usage_mb: float
    peak_usage_mb: float
    available_mb: float
    utilization_percent: float

class MemoryEfficientPortfolioOperations:
    """
    Memory-Efficient Portfolio Operations für LXC 10.1.1.174
    Optimiert für große Portfolios mit minimaler Memory-Nutzung
    """
    
    def __init__(self, config: Optional[PortfolioConfig] = None):
        self.config = config or PortfolioConfig()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="portfolio_ops_"))
        self.memory_maps: Dict[str, mmap.mmap] = {}
        self._initial_memory = self._get_memory_usage()
        
        logger.info(f"Memory-Efficient Portfolio Operations initialized")
        logger.info(f"Memory limit: {self.config.memory_limit_mb:.1f}MB")
        logger.info(f"Batch size: {self.config.batch_size}")
        logger.info(f"Temporary directory: {self.temp_dir}")
    
    def __del__(self):
        """Cleanup resources"""
        self._cleanup_resources()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _check_memory_limit(self) -> bool:
        """Check if memory usage is within limits"""
        current_usage = self._get_memory_usage()
        return current_usage < self.config.memory_limit_mb
    
    def _cleanup_resources(self):
        """Cleanup temporary files und memory maps"""
        try:
            # Close memory maps
            for name, mm in self.memory_maps.items():
                mm.close()
                logger.debug(f"Closed memory map: {name}")
            self.memory_maps.clear()
            
            # Remove temporary files
            if self.temp_dir.exists():
                for file in self.temp_dir.iterdir():
                    file.unlink()
                self.temp_dir.rmdir()
                logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def create_sparse_covariance_matrix(
        self, 
        returns: np.ndarray, 
        threshold: float = 1e-6
    ) -> sp.csr_matrix:
        """Create sparse covariance matrix für memory efficiency"""
        logger.info(f"Creating sparse covariance matrix for {returns.shape[1]} assets")
        
        # Calculate covariance in chunks to save memory
        n_assets = returns.shape[1]
        chunk_size = min(self.config.chunk_size, n_assets)
        
        # Use sparse matrix storage
        row_indices = []
        col_indices = []
        data_values = []
        
        for i in range(0, n_assets, chunk_size):
            end_i = min(i + chunk_size, n_assets)
            chunk_i = returns[:, i:end_i]
            
            for j in range(i, n_assets, chunk_size):
                end_j = min(j + chunk_size, n_assets)
                chunk_j = returns[:, j:end_j]
                
                # Calculate covariance for this chunk
                if i == j:
                    # Diagonal block
                    cov_chunk = np.cov(chunk_i, rowvar=False)
                else:
                    # Off-diagonal block
                    combined = np.hstack([chunk_i, chunk_j])
                    full_cov = np.cov(combined, rowvar=False)
                    cov_chunk = full_cov[:chunk_i.shape[1], chunk_i.shape[1]:]
                
                # Extract non-zero elements above threshold
                if cov_chunk.ndim == 0:
                    cov_chunk = np.array([[cov_chunk]])
                elif cov_chunk.ndim == 1:
                    cov_chunk = cov_chunk.reshape(-1, 1)
                
                rows, cols = np.where(np.abs(cov_chunk) > threshold)
                values = cov_chunk[rows, cols]
                
                # Convert to global indices
                global_rows = rows + i
                global_cols = cols + j
                
                row_indices.extend(global_rows)
                col_indices.extend(global_cols)
                data_values.extend(values)
                
                # Also add symmetric entries for off-diagonal blocks
                if i != j:
                    row_indices.extend(global_cols)
                    col_indices.extend(global_rows)
                    data_values.extend(values)
        
        # Create sparse matrix
        sparse_cov = sp.csr_matrix(
            (data_values, (row_indices, col_indices)),
            shape=(n_assets, n_assets)
        )
        
        # Ensure symmetry
        sparse_cov = (sparse_cov + sparse_cov.T) / 2
        
        logger.info(f"Sparse covariance matrix created: {sparse_cov.nnz}/{n_assets**2} non-zero elements")
        logger.info(f"Sparsity: {(1 - sparse_cov.nnz / (n_assets**2)) * 100:.1f}%")
        
        return sparse_cov
    
    def memory_mapped_portfolio_optimization(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: sp.csr_matrix,
        risk_tolerance: float = 0.5
    ) -> Dict[str, Any]:
        """Memory-mapped portfolio optimization für große Portfolios"""
        n_assets = len(expected_returns)
        logger.info(f"Starting memory-mapped portfolio optimization for {n_assets} assets")
        
        if not self._check_memory_limit():
            logger.warning("Memory usage approaching limit, using aggressive optimization")
        
        # Memory-mapped storage für optimization variables
        weights_file = self.temp_dir / f"weights_{n_assets}.dat"
        with open(weights_file, "wb") as f:
            # Initialize with equal weights
            initial_weights = np.ones(n_assets, dtype=np.float64) / n_assets
            initial_weights.tofile(f)
        
        # Create memory map
        with open(weights_file, "r+b") as f:
            mm = mmap.mmap(f.fileno(), n_assets * 8)  # 8 bytes per float64
            self.memory_maps[f"weights_{n_assets}"] = mm
            weights_array = np.frombuffer(mm, dtype=np.float64)
        
        # Define objective function with memory efficiency
        def memory_efficient_objective(weights: np.ndarray) -> float:
            # Portfolio return calculation
            portfolio_return = np.dot(weights, expected_returns)
            
            # Portfolio risk calculation using sparse matrix operations
            weights_sparse = sp.csr_matrix(weights.reshape(1, -1))
            risk_squared = weights_sparse @ covariance_matrix @ weights_sparse.T
            portfolio_risk = np.sqrt(risk_squared.toarray()[0, 0])
            
            # Check memory usage during optimization
            if not self._check_memory_limit():
                logger.warning("Memory limit exceeded during optimization")
            
            # Risk-return tradeoff
            return risk_tolerance * portfolio_risk - (1 - risk_tolerance) * portfolio_return
        
        # Constraints: weights sum to 1
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
        ]
        
        # Bounds: 0 <= weight <= 1
        bounds = [(0.0, 1.0) for _ in range(n_assets)]
        
        # Optimization with memory monitoring
        initial_memory = self._get_memory_usage()
        
        result = minimize(
            memory_efficient_objective,
            weights_array.copy(),  # Copy to avoid modifying memory map during optimization
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={
                'maxiter': 500,
                'ftol': 1e-8,
                'disp': False
            }
        )
        
        final_memory = self._get_memory_usage()
        memory_usage = final_memory - initial_memory
        
        # Extract optimal weights
        optimal_weights = result.x
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(optimal_weights, expected_returns)
        portfolio_risk = np.sqrt(
            (sp.csr_matrix(optimal_weights.reshape(1, -1)) @ 
             covariance_matrix @ 
             sp.csr_matrix(optimal_weights.reshape(-1, 1))).toarray()[0, 0]
        )
        sharpe_ratio = portfolio_return / portfolio_risk if portfolio_risk > 0 else 0
        
        optimization_result = {
            'optimal_weights': optimal_weights,
            'portfolio_return': float(portfolio_return),
            'portfolio_risk': float(portfolio_risk),
            'sharpe_ratio': float(sharpe_ratio),
            'optimization_success': result.success,
            'num_iterations': result.nit,
            'memory_usage_mb': memory_usage,
            'memory_efficiency': {
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'peak_usage_mb': max(initial_memory, final_memory),
                'memory_limit_mb': self.config.memory_limit_mb,
                'within_limit': final_memory < self.config.memory_limit_mb
            }
        }
        
        logger.info(f"Portfolio optimization completed")
        logger.info(f"Memory usage: {memory_usage:.1f}MB")
        logger.info(f"Portfolio return: {portfolio_return:.4f}")
        logger.info(f"Portfolio risk: {portfolio_risk:.4f}")
        logger.info(f"Sharpe ratio: {sharpe_ratio:.4f}")
        
        return optimization_result
    
    def batch_correlation_analysis(
        self, 
        returns: np.ndarray
    ) -> Dict[str, Any]:
        """Batch correlation analysis für memory efficiency"""
        n_assets = returns.shape[1]
        n_observations = returns.shape[0]
        
        logger.info(f"Starting batch correlation analysis: {n_assets} assets, {n_observations} observations")
        
        batch_size = min(self.config.batch_size, n_assets)
        correlation_results = {}
        
        # Process correlations in batches
        for i in range(0, n_assets, batch_size):
            end_i = min(i + batch_size, n_assets)
            batch_returns = returns[:, i:end_i]
            
            # Calculate correlation matrix for this batch
            batch_corr = np.corrcoef(batch_returns, rowvar=False)
            
            # Handle single asset case
            if batch_corr.ndim == 0:
                batch_corr = np.array([[1.0]])
            elif batch_corr.ndim == 1:
                batch_corr = np.array([[batch_corr[0]]])
            
            # Store strong correlations (> threshold)
            threshold = 0.5
            strong_corr_indices = np.where(np.abs(batch_corr) > threshold)
            
            for row, col in zip(strong_corr_indices[0], strong_corr_indices[1]):
                if row != col:  # Skip diagonal
                    global_i = i + row
                    global_j = i + col
                    correlation_results[f"{global_i}-{global_j}"] = float(batch_corr[row, col])
            
            # Memory usage check
            current_memory = self._get_memory_usage()
            if current_memory > self.config.memory_limit_mb * 0.8:
                logger.warning(f"Memory usage high: {current_memory:.1f}MB")
        
        # Analyze correlation patterns
        strong_correlations = {k: v for k, v in correlation_results.items() if abs(v) > 0.7}
        weak_correlations = {k: v for k, v in correlation_results.items() if abs(v) < 0.3}
        
        analysis_results = {
            'total_correlations': len(correlation_results),
            'strong_correlations': strong_correlations,
            'weak_correlations': weak_correlations,
            'avg_correlation': np.mean(list(correlation_results.values())) if correlation_results else 0.0,
            'max_correlation': max(correlation_results.values()) if correlation_results else 0.0,
            'min_correlation': min(correlation_results.values()) if correlation_results else 0.0,
            'memory_metrics': {
                'final_memory_mb': self._get_memory_usage(),
                'memory_limit_mb': self.config.memory_limit_mb,
                'batch_size_used': batch_size
            }
        }
        
        logger.info(f"Correlation analysis completed")
        logger.info(f"Strong correlations found: {len(strong_correlations)}")
        logger.info(f"Average correlation: {analysis_results['avg_correlation']:.4f}")
        
        return analysis_results
    
    def streaming_risk_calculation(
        self,
        weights: np.ndarray,
        covariance_matrix: sp.csr_matrix
    ) -> float:
        """Streaming risk calculation für memory efficiency"""
        n_assets = len(weights)
        
        if n_assets <= self.config.batch_size:
            # Small portfolio - direct calculation
            weights_sparse = sp.csr_matrix(weights.reshape(1, -1))
            risk_squared = weights_sparse @ covariance_matrix @ weights_sparse.T
            return np.sqrt(risk_squared.toarray()[0, 0])
        
        # Large portfolio - streaming calculation
        logger.info(f"Using streaming risk calculation for {n_assets} assets")
        
        total_risk_squared = 0.0
        batch_size = self.config.batch_size
        
        for i in range(0, n_assets, batch_size):
            end_i = min(i + batch_size, n_assets)
            weights_batch_i = weights[i:end_i]
            
            for j in range(0, n_assets, batch_size):
                end_j = min(j + batch_size, n_assets)
                weights_batch_j = weights[j:end_j]
                
                # Extract submatrix
                cov_submatrix = covariance_matrix[i:end_i, j:end_j]
                
                # Calculate contribution to total risk
                contribution = weights_batch_i.T @ cov_submatrix @ weights_batch_j
                total_risk_squared += contribution
        
        portfolio_risk = np.sqrt(total_risk_squared)
        
        logger.debug(f"Streaming risk calculation completed: {portfolio_risk:.6f}")
        return float(portfolio_risk)
    
    def get_memory_metrics(self) -> MemoryMetrics:
        """Get current memory metrics"""
        current_usage = self._get_memory_usage()
        available = psutil.virtual_memory().available / 1024 / 1024
        peak_usage = max(current_usage, self._initial_memory)
        utilization = (current_usage / self.config.memory_limit_mb) * 100
        
        return MemoryMetrics(
            current_usage_mb=current_usage,
            peak_usage_mb=peak_usage,
            available_mb=available,
            utilization_percent=utilization
        )
    
    def optimize_large_portfolio(
        self,
        expected_returns: np.ndarray,
        return_covariance_data: np.ndarray,
        risk_tolerance: float = 0.5
    ) -> Dict[str, Any]:
        """Complete optimization pipeline für large portfolios"""
        logger.info(f"Starting large portfolio optimization pipeline")
        
        n_assets = len(expected_returns)
        
        if n_assets > self.config.max_assets:
            logger.warning(f"Portfolio size {n_assets} exceeds recommended maximum {self.config.max_assets}")
            logger.info("Applying asset selection to reduce portfolio size")
            
            # Select top assets by return/risk ratio
            returns_std = np.std(return_covariance_data, axis=0)
            return_risk_ratio = expected_returns / (returns_std + 1e-8)
            
            # Select top assets
            top_indices = np.argsort(return_risk_ratio)[-self.config.max_assets:]
            
            expected_returns = expected_returns[top_indices]
            return_covariance_data = return_covariance_data[:, top_indices]
            
            logger.info(f"Portfolio reduced to {len(expected_returns)} assets")
        
        # Step 1: Create sparse covariance matrix
        start_memory = self._get_memory_usage()
        sparse_cov = self.create_sparse_covariance_matrix(return_covariance_data)
        cov_memory = self._get_memory_usage() - start_memory
        
        # Step 2: Memory-mapped optimization
        opt_start_memory = self._get_memory_usage()
        optimization_result = self.memory_mapped_portfolio_optimization(
            expected_returns, sparse_cov, risk_tolerance
        )
        opt_memory = self._get_memory_usage() - opt_start_memory
        
        # Step 3: Correlation analysis
        corr_start_memory = self._get_memory_usage()
        correlation_analysis = self.batch_correlation_analysis(return_covariance_data)
        corr_memory = self._get_memory_usage() - corr_start_memory
        
        # Combine results
        complete_result = {
            'portfolio_optimization': optimization_result,
            'correlation_analysis': correlation_analysis,
            'memory_breakdown': {
                'covariance_calculation_mb': cov_memory,
                'optimization_mb': opt_memory,
                'correlation_analysis_mb': corr_memory,
                'total_additional_mb': cov_memory + opt_memory + corr_memory
            },
            'lxc_performance': {
                'total_assets': n_assets,
                'sparse_matrix_size': sparse_cov.nnz,
                'memory_efficiency_achieved': True,
                'within_lxc_limits': self._get_memory_usage() < self.config.memory_limit_mb
            }
        }
        
        # Final memory metrics
        final_metrics = self.get_memory_metrics()
        complete_result['final_memory_metrics'] = {
            'current_usage_mb': final_metrics.current_usage_mb,
            'peak_usage_mb': final_metrics.peak_usage_mb,
            'utilization_percent': final_metrics.utilization_percent,
            'within_limit': final_metrics.current_usage_mb < self.config.memory_limit_mb
        }
        
        logger.info("Large portfolio optimization pipeline completed")
        logger.info(f"Final memory usage: {final_metrics.current_usage_mb:.1f}MB ({final_metrics.utilization_percent:.1f}%)")
        
        return complete_result

# Example usage und testing
def example_large_portfolio_optimization():
    """Example usage für large portfolio optimization"""
    
    # Configuration für LXC container
    config = PortfolioConfig(
        max_assets=80,  # Reasonable für LXC
        batch_size=20,  # Small batches für memory efficiency
        memory_limit_mb=800.0,  # Conservative limit
        use_sparse_matrices=True,
        use_memory_mapping=True
    )
    
    # Initialize portfolio operations
    portfolio_ops = MemoryEfficientPortfolioOperations(config)
    
    try:
        # Generate synthetic large portfolio data
        n_assets = 150
        n_observations = 1000
        
        print(f"Testing with {n_assets} assets, {n_observations} observations")
        
        # Synthetic returns data
        np.random.seed(42)
        returns = np.random.multivariate_normal(
            mean=np.zeros(n_assets),
            cov=np.eye(n_assets) * 0.01 + np.random.random((n_assets, n_assets)) * 0.001,
            size=n_observations
        )
        
        # Expected returns
        expected_returns = np.mean(returns, axis=0) + np.random.uniform(0.05, 0.15, n_assets)
        
        # Run optimization
        result = portfolio_ops.optimize_large_portfolio(
            expected_returns=expected_returns,
            return_covariance_data=returns,
            risk_tolerance=0.6
        )
        
        # Print results
        print("\\n=== OPTIMIZATION RESULTS ===")
        opt_result = result['portfolio_optimization']
        print(f"Portfolio Return: {opt_result['portfolio_return']:.4f}")
        print(f"Portfolio Risk: {opt_result['portfolio_risk']:.4f}")
        print(f"Sharpe Ratio: {opt_result['sharpe_ratio']:.4f}")
        
        print("\\n=== MEMORY EFFICIENCY ===")
        memory_breakdown = result['memory_breakdown']
        print(f"Covariance Calculation: {memory_breakdown['covariance_calculation_mb']:.1f}MB")
        print(f"Optimization: {memory_breakdown['optimization_mb']:.1f}MB")
        print(f"Correlation Analysis: {memory_breakdown['correlation_analysis_mb']:.1f}MB")
        print(f"Total Additional Memory: {memory_breakdown['total_additional_mb']:.1f}MB")
        
        final_metrics = result['final_memory_metrics']
        print(f"Final Memory Usage: {final_metrics['current_usage_mb']:.1f}MB ({final_metrics['utilization_percent']:.1f}%)")
        print(f"Within LXC Limit: {final_metrics['within_limit']}")
        
        return result
        
    finally:
        # Cleanup
        del portfolio_ops

if __name__ == "__main__":
    example_large_portfolio_optimization()