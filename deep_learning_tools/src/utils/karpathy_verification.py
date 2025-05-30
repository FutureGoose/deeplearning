"""
Implements verification tests and utilities based on Andrej Karpathy's 
'A Recipe for Training Neural Networks' blog post: https://karpathy.github.io/2019/04/25/recipe/
"""

import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Any
from torch.utils.data import DataLoader

class KarpathyVerification:
    """
    A collection of verification tests for neural network training
    as recommended by Andrej Karpathy's blog post.
    """
    
    def __init__(
        self,
        model: nn.Module,
        criterion: nn.Module,
        optimizer: torch.optim.Optimizer,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: torch.device,
        verbose: bool = True,
        use_half_precision: bool = False,
        use_channels_last: bool = False
    ):
        self.model = model
        self.criterion = criterion
        self.optimizer = optimizer
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.verbose = verbose
        self.use_half_precision = use_half_precision
        self.use_channels_last = use_channels_last
        
        # store human baselines for common datasets
        self.human_baselines = {
            'MNIST': 99.8,
            'FashionMNIST': 83.5,
            'CIFAR10': 94.0,
            'CIFAR100': 77.0,
            'ImageNet': 95.2
        }
    
    def _print(self, msg: str, color: str = "white", bold: bool = False) -> None:
        """Helper method for consistent colored output"""
        if not self.verbose:
            return
            
        colors = {
            "white": "\033[38;5;252m",
            "green": "\033[38;5;40m",
            "yellow": "\033[38;5;226m",
            "red": "\033[38;5;196m"
        }
        
        style = "\033[1m" if bold else ""
        color_code = colors.get(color, colors["white"])
        print(f"{color_code}{style}{msg}\033[0m")
        
    def verify_init_loss(self) -> Dict[str, float]:
        """
        Verifies that the loss starts at the correct value.
        For classification with CrossEntropyLoss, should be close to -log(1/n_classes).
        """
        self._print("\n🔍 Checking Initial Loss", bold=True)
        self._print("Initial loss should be close to -log(1/n_classes) for random predictions.")
        self._print("This verifies proper weight initialization.\n")
            
        self.model.eval()
        results = {}
        
        with torch.no_grad():
            # get a single batch
            data, targets = next(iter(self.train_loader))
            
            # move data to device first
            data, targets = data.to(self.device), targets.to(self.device)
            
            # convert to channels last if enabled
            if self.use_channels_last and data.dim() == 4:
                data = data.to(memory_format=torch.channels_last)
            
            # convert to half precision if enabled
            if self.use_half_precision:
                data = data.half()
            
            # normal forward pass
            outputs = self.model(data)
            init_loss = self.criterion(outputs, targets).item()
            results['initial_loss'] = init_loss
            
            if isinstance(self.criterion, nn.CrossEntropyLoss):
                n_classes = outputs.size(1)
                expected_loss = -np.log(1/n_classes)
                results['expected_random_loss'] = expected_loss
                
                self._print(f"Initial loss: {init_loss:.4f}", color="green")
                self._print(f"Expected loss for random predictions: {expected_loss:.4f}", color="green")
                
                # check if initial loss is reasonable (allow 20% deviation)
                loss_deviation = abs(init_loss - expected_loss) / expected_loss
                if loss_deviation > 0.2:
                    self._print(f"⚠️  Initial loss deviates by {loss_deviation*100:.1f}% from expected!", color="yellow")
                    self._print("This might indicate improper weight initialization.", color="yellow")
                else:
                    self._print("✅ Initial loss matches expected value", color="green")
        
        return results
        
    def verify_input_independence(self) -> Dict[str, float]:
        """
        Verifies that the model performs better on real data than zero input.
        This shows if the model actually extracts information from the input.
        """
        self._print("\n🎯 Testing Input Dependence", bold=True)
        self._print("Model should perform better on real data than zero input.")
        self._print("This verifies the model actually uses input information.\n")
        
        self.model.eval()
        results = {}
        
        with torch.no_grad():
            # get a single batch
            data, targets = next(iter(self.train_loader))
            
            # move data to device first
            data, targets = data.to(self.device), targets.to(self.device)
            
            # convert to channels last if enabled
            if self.use_channels_last and data.dim() == 4:
                data = data.to(memory_format=torch.channels_last)
            
            # convert to half precision if enabled
            if self.use_half_precision:
                data = data.half()
            
            # normal forward pass
            outputs = self.model(data)
            normal_loss = self.criterion(outputs, targets).item()
            results['normal_loss'] = normal_loss
            
            # zero input baseline (match data type and format)
            zero_data = torch.zeros_like(data)
            if self.use_channels_last and zero_data.dim() == 4:
                zero_data = zero_data.to(memory_format=torch.channels_last)
            if self.use_half_precision:
                zero_data = zero_data.half()
            
            zero_outputs = self.model(zero_data)
            zero_loss = self.criterion(zero_outputs, targets).item()
            results['zero_input_loss'] = zero_loss
            
            # compare performances
            loss_diff = zero_loss - normal_loss
            results['loss_difference'] = loss_diff
            
            self._print(f"Normal input loss: {normal_loss:.4f}", color="green")
            self._print(f"Zero input loss: {zero_loss:.4f}", color="green")
            
            if loss_diff < 0:
                self._print(f"❌ Loss difference is negative: {loss_diff:.4f}", color="red")
                self._print("Model performs worse on real data than zero input!", color="red")
                self._print("Suggestions:", color="yellow")
                self._print("1. Check weight initialization", color="yellow")
                self._print("2. Verify input normalization", color="yellow")
                self._print("3. Ensure model architecture is correct", color="yellow")
            else:
                self._print(f"✅ Loss difference is positive: {loss_diff:.4f}", color="green")
                self._print("Model successfully extracts information from input", color="green")
        
        return results
        
    def track_predictions(self, data: torch.Tensor, targets: torch.Tensor) -> Dict[str, Any]:
        """
        Tracks predictions for a fixed batch of data.
        """
        self.model.eval()
        with torch.no_grad():
            # convert to channels last if enabled
            if self.use_channels_last and data.dim() == 4:
                data = data.to(memory_format=torch.channels_last)
            
            # convert to half precision if enabled
            if self.use_half_precision:
                data = data.half()
            
            outputs = self.model(data)
            loss = self.criterion(outputs, targets).item()
            
            if isinstance(self.criterion, nn.CrossEntropyLoss):
                predictions = outputs.argmax(dim=1)
            else:
                predictions = outputs
                
        return {
            'predictions': predictions.cpu().numpy(),
            'loss': loss
        }
    
    def overfit_one_batch(
        self,
        max_iters: int = 1000,
        target_loss: float = 0.01,  # relaxed target loss
        num_examples: int = 2
    ) -> Tuple[List[float], bool]:
        """
        Attempts to overfit a tiny batch (2-3 examples) of data.
        This is a debugging tool to verify the model can reach minimal loss.
        """
        self._print("\n🎯 Testing Model Capacity", bold=True)
        self._print(f"Attempting to overfit {num_examples} examples. Success indicates the model has sufficient capacity.")
        self._print(f"Target loss: {target_loss:.4f}")
        self._print("Loss should decrease rapidly and reach near-zero.\n")
        
        # get a single batch and take only first few examples
        data, targets = next(iter(self.train_loader))
        data, targets = data[:num_examples], targets[:num_examples]
        data, targets = data.to(self.device), targets.to(self.device)

        # convert to channels last if enabled
        if self.use_channels_last and data.dim() == 4:
            data = data.to(memory_format=torch.channels_last)
        
        # convert to half precision if enabled
        if self.use_half_precision:
            data = data.half()
        
        initial_loss = None
        losses = []
        target_reached = False
        plateau_counter = 0
        plateau_threshold = 50  # number of iterations to consider as plateau
        
        for i in range(max_iters):
            self.optimizer.zero_grad()
            outputs = self.model(data)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()
            
            current_loss = loss.item()
            if initial_loss is None:
                initial_loss = current_loss
                
            losses.append(current_loss)
            
            # check for plateaus
            if len(losses) > plateau_threshold:
                recent_losses = losses[-plateau_threshold:]
                loss_std = np.std(recent_losses)
                if loss_std < 1e-6:  # very small variation indicates plateau
                    plateau_counter += 1
                else:
                    plateau_counter = 0
                    
            if i % 100 == 0:
                self._print(f"Iteration {i}: Loss = {current_loss:.6f}", color="green")
                if i > 0:
                    loss_reduction = (initial_loss - current_loss) / initial_loss * 100
                    self._print(f"Loss reduced by {loss_reduction:.1f}%", color="green")
                
            if current_loss < target_loss:
                self._print(f"✅ Target loss reached at iteration {i}", color="green")
                target_reached = True
                break
                
            if plateau_counter >= 5:  # 5 consecutive plateau detections
                self._print("\n⚠️  Training has plateaued", color="yellow")
                break
                
        if not target_reached:
            self._print("❌ Failed to reach target loss", color="red")
            final_loss_reduction = (initial_loss - current_loss) / initial_loss * 100
            self._print(f"Total loss reduction: {final_loss_reduction:.1f}%", color="yellow")
            
            if final_loss_reduction < 50:
                self._print("Poor loss reduction might indicate:", color="yellow")
                self._print("1. Insufficient model capacity", color="yellow")
                self._print("2. Learning rate too low", color="yellow")
                self._print("3. Optimization issues", color="yellow")
                
        return losses, target_reached
    
    def _scale_for_visualization(self, img: np.ndarray) -> np.ndarray:
        """Scales image data to [0, 1] range for visualization"""
        img = img - img.min()
        img = img / (img.max() + 1e-8)
        return img
    
    def visualize_batch(self, num_samples: int = 8) -> None:
        """
        Visualizes a batch of data exactly as it enters the network.
        This helps verify preprocessing and augmentation.
        """
        self._print("\n👁️ Visualizing Network Input", bold=True)
        self._print("Showing data exactly as it enters the model. Verify:")
        self._print("1. Images are properly normalized/preprocessed")
        self._print("2. Labels match the images")
        self._print("3. No unintended transformations\n")
            
        # get a single batch
        data, targets = next(iter(self.train_loader))
        
        # print data statistics to help debug normalization
        self._print(f"Data range: [{data.min():.4f}..{data.max():.4f}]", color="green")
        self._print(f"Data mean: {data.mean():.4f}, std: {data.std():.4f}\n", color="green")
        
        # limit to num_samples
        data = data[:num_samples]
        targets = targets[:num_samples]
        
        # create a grid of images
        num_rows = (num_samples + 3) // 4  # ceil(num_samples/4)
        fig, axes = plt.subplots(num_rows, min(4, num_samples), figsize=(12, 3*num_rows))
        if num_samples == 1:
            axes = np.array([axes])
        axes = axes.flatten()
        
        for i in range(num_samples):
            img = data[i]
            label = targets[i].item()
            
            # convert to numpy and handle different channel configurations
            if img.shape[0] == 1:  # grayscale
                img = img.squeeze().numpy()
                img = self._scale_for_visualization(img)
                axes[i].imshow(img, cmap='gray')
            else:  # RGB/BGR
                img = img.permute(1, 2, 0).numpy()
                img = self._scale_for_visualization(img)
                axes[i].imshow(img)
            
            axes[i].axis('off')
            axes[i].set_title(f'Label: {label}')
        
        plt.tight_layout()
        plt.show()
    
    def plot_prediction_dynamics(
        self,
        prediction_history: List[Dict[str, Any]]
    ) -> None:
        """
        Visualizes how predictions changed during training.
        """
        self._print("\n📈 Analyzing Prediction Dynamics", bold=True)
        self._print("Left: Loss should decrease smoothly. Spikes indicate instability.")
        self._print("Right: Class predictions should stabilize over time. Excessive changes suggest learning issues.\n")
            
        losses = [info['loss'] for info in prediction_history]
        predictions = np.array([info['predictions'] for info in prediction_history])
        
        # print some statistics
        self._print(f"Initial loss: {losses[0]:.4f}", color="green")
        self._print(f"Final loss: {losses[-1]:.4f}", color="green")
        self._print(f"Loss reduction: {losses[0] - losses[-1]:.4f}\n", color="green")
        
        # plot loss dynamics
        plt.figure(figsize=(10, 4))
        plt.subplot(1, 2, 1)
        plt.plot(losses)
        plt.title('Loss on Fixed Batch')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        
        # plot prediction dynamics for first few samples
        plt.subplot(1, 2, 2)
        num_samples = min(5, predictions.shape[1])
        for i in range(num_samples):
            plt.plot(predictions[:, i], label=f'Sample {i}')
        plt.title('Prediction Dynamics')
        plt.xlabel('Epoch')
        plt.ylabel('Predicted Class')
        plt.legend()
        
        plt.tight_layout()
        plt.show()
    
    def run_all_verifications(
        self,
        run_overfit_test: bool = True,
        max_overfit_iters: int = 1000,
        visualize_samples: int = 8
    ) -> Dict[str, Any]:
        """
        Runs all verification tests and returns the results.
        """
        self._print("\n🚀 Running Karpathy's Verification Tests", bold=True)
        self._print("These tests help verify the training setup and catch common issues early.\n")
            
        results = {}
        
        # 1. Verify initialization loss
        results['init_verification'] = self.verify_init_loss()
        
        # 2. Verify input independence
        results['input_independence'] = self.verify_input_independence()
        
        # 3. Visualize batch
        self.visualize_batch(num_samples=visualize_samples)
            
        # 4. Overfit one batch (optional as it modifies model weights)
        if run_overfit_test:
            # Save states
            state_dict = self.model.state_dict()
            optimizer_state = self.optimizer.state_dict()
            
            losses, success = self.overfit_one_batch(max_iters=max_overfit_iters)
            results['overfit_test'] = {
                'losses': losses,
                'success': success
            }
            
            # restore states
            self.model.load_state_dict(state_dict)
            self.optimizer.load_state_dict(optimizer_state)
            self.model.train()  # ensure model is in training mode
            
        self._print("\n✅ Verification Tests Completed", bold=True)
        self._print("Review the results above to ensure your training setup is solid.\n")
            
        return results 