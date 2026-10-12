"""Standard experiment tracker and W&B live synchronizer for diffusion runs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import wandb
    _WANDB_AVAILABLE = True
except ImportError:
    _WANDB_AVAILABLE = False


class ExperimentTracker:
    def __init__(
        self,
        output_dir: str | Path,
        config: dict[str, Any] | None = None,
        use_wandb: bool = True,
        wandb_project: str = "celeba-flow-dit",
        wandb_entity: str | None = None,
        wandb_name: str | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir = self.output_dir / "checkpoints"
        self.figures_dir = self.output_dir / "figures"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.output_dir / "metrics.jsonl"
        self.config_file = self.output_dir / "config.json"

        if config is not None and not self.config_file.exists():
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)

        self.use_wandb = use_wandb and _WANDB_AVAILABLE
        self.wandb_run = None
        if self.use_wandb:
            try:
                self.wandb_run = wandb.init(
                    project=wandb_project,
                    entity=wandb_entity,
                    name=wandb_name or self.output_dir.name,
                    config=config,
                    reinit=True,
                )
            except Exception as e:
                print(f"[Tracker] Warning: could not initialize wandb: {e}")
                self.use_wandb = False

    def log_metrics(self, step: int, epoch: int, metrics: dict[str, float]) -> None:
        payload = {
            "step": int(step),
            "epoch": int(epoch),
            "timestamp": time.time(),
            **{k: float(v) for k, v in metrics.items()},
        }
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(payload) + "\n")

        if self.use_wandb and self.wandb_run is not None:
            try:
                wandb.log(payload, step=int(step))
            except Exception:
                pass

    def log_image(self, step: int, tag: str, image_path: str | Path, caption: str | None = None) -> None:
        if self.use_wandb and self.wandb_run is not None:
            try:
                wandb.log({tag: wandb.Image(str(image_path), caption=caption or f"Step {step}")}, step=int(step))
            except Exception:
                pass

    def plot_loss_curve(self, output_path: str | Path | None = None) -> Path | None:
        if not self.metrics_file.exists():
            return None
        steps, losses = [], []
        with open(self.metrics_file, "r") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if "step" in d and "loss" in d:
                        steps.append(d["step"])
                        losses.append(d["loss"])
                except Exception:
                    continue
        if not steps:
            return None
        plt.figure(figsize=(10, 5), dpi=150)
        plt.plot(steps, losses, label="Loss", color="#1f77b4")
        plt.xlabel("Step")
        plt.ylabel("Loss")
        plt.title(f"Loss Curve - {self.output_dir.name}")
        plt.grid(True, linestyle=":", alpha=0.6)
        plt.legend()
        plt.tight_layout()
        target = Path(output_path) if output_path else self.figures_dir / "loss_curve.png"
        plt.savefig(target)
        plt.close()
        return target

    def finish(self) -> None:
        if self.use_wandb and self.wandb_run is not None:
            try:
                self.wandb_run.finish()
            except Exception:
                pass
