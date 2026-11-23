"""CPU marching cubes adapter installed into the isolated TripoSR checkout."""
import torch
from skimage.measure import marching_cubes as extract


def marching_cubes(field, level):
    vertices, faces, _, _ = extract(field.cpu().numpy(), level=level)
    return torch.from_numpy(vertices[:, ::-1].copy()), torch.from_numpy(faces.copy()).long()
