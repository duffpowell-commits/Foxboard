# Prepare images for Forge 3D

Forge 3D uses one image to reconstruct a textured draft. Keep the full turnaround as your design reference and upload one clean view per job. The source image and output are public in this repository.

## Full-body input

- Use a straight-on, full-body image of one character. Keep hair, fingertips, and soles in frame with a little margin.
- For humanoids, use a shallow A-pose with gray space between hands and hips and a gap between the legs. Keep the fingers relaxed and visibly separated.
- Use an even, plain background and soft lighting. Skip captions, floor shadows, borders, props, and overlapping costume parts.
- Compare the preparatory image to the approved art before queuing. Check body proportions, hair direction, asymmetrical markings, costume fit, and shoe shape.

## Start close when likeness matters

For the Duff Quest test, the full-body image established the silhouette and outfit colors, but the face and fingers came out distorted. A separate head-and-shoulders crop of the same image preserved a clearer nose, jaw, and hairstyle. Start with a bust if the face is the priority, or use one bust job and one full-body job when both matter. The bust should show all the hair, both ears where visible, and the neck. Keep the source lighting and angle consistent.

A front image leaves the profile and back for the model to infer. Keep matching profile and back views nearby to review the draft and guide sculpt cleanup. Forge's current workflow takes a single image per run.

## Upload and review

Forge accepts PNG or JPEG with a longest edge of 768 pixels. The encoded reference file must be at most 1,000,000 bytes. Resize proportionally and keep the high-resolution master separately.

Review the textured GLB front-on and at three-quarter view, then at gameplay size. Check the face profile, hair silhouette, fingers, hand-to-hip gaps, and material boundaries before rigging. If the geometry is sound and the front texture is blurry, try projecting the approved reference onto the front and blend into the existing side texture. If anatomy or proportions are wrong, fix the sculpt or try a cleaner input before spending time on the texture.

Change one thing per test and compare at the same angle and zoom. Save the approved reference, raw GLB, and refined GLB separately.
