# FaceLock Module 1 - Face Recognition System

Module 1 is the foundation of the whole FaceLock project. Everything else in the roadmap depends on this part being reliable, because every locked app, launcher wrapper, and background daemon will eventually ask one question: “Is this the owner?”

This document explains what Module 1 is supposed to do, what you need before you start, which files to create first, and how the pieces fit together. It is written as a learning guide, not just as implementation notes.

## What Module 1 Must Do

The goal is to build a small face authentication prototype with this flow:

1. Open the webcam.
2. Detect a face.
3. Collect multiple face samples during enrollment.
4. Convert those samples into face embeddings.
5. Save the embeddings locally.
6. Compare new webcam frames against the saved embedding.
7. Print or return either `Authenticated` or `Denied`.

At this stage, do not think about locking apps yet. Do not think about the GUI either. Module 1 should prove that face recognition works in isolation.

## What You Need Before You Start

You need a few things in place before writing code:

1. Python 3.11 or newer.
2. A working webcam.
3. A Linux environment with camera permissions.
4. A face detection / encoding library.
5. A place to store the enrolled face data.

### Recommended Python Packages

For a first version, use:

- `opencv-python` for webcam access and image handling.
- `numpy` for frame and vector operations.
- One face encoding library:
  - `face_recognition` if you want the easiest conceptual path and can install `dlib` successfully.
  - `insightface` if you want a more modern model and are okay with a slightly heavier setup.

If your main goal is learning the architecture, `face_recognition` is fine as a prototype. If your main goal is long-term Linux reliability, you may later replace it with a more robust embedding model.

### Important Design Rule

Do not store raw face images as the final authentication artifact.

Store embeddings and metadata instead, because embeddings are the actual comparison data and are smaller, faster, and more appropriate for authentication.

## The Best Order to Build It

Build Module 1 in this order:

1. Webcam capture only.
2. Face detection on a single frame.
3. Enrollment capture loop.
4. Embedding extraction.
5. Save and load enrollment data.
6. Authentication comparison.
7. Small command-line test entry point.

This order matters because each step gives you a testable checkpoint. If you try to build the whole pipeline at once, you will not know which part failed.

## Recommended File Structure For Module 1

Start with a small, focused structure. Do not create every roadmap folder yet. Only create what Module 1 needs.

```text
facelock/
├── module1.md
├── pyproject.toml
├── README.md
├── src/
│   └── facelock/
│       ├── __init__.py
│       └── auth/
│           ├── __init__.py
│           ├── camera.py
│           ├── detector.py
│           ├── encoder.py
│           ├── storage.py
│           └── service.py
├── data/
│   └── face_encoding.pkl
└── tests/
    ├── test_camera.py
    ├── test_detector.py
    ├── test_encoder.py
    └── test_storage.py
```

### Why This Structure Works

- `src/facelock/auth/camera.py` isolates webcam reading.
- `src/facelock/auth/detector.py` handles face detection logic.
- `src/facelock/auth/encoder.py` turns a detected face into a vector.
- `src/facelock/auth/storage.py` loads and saves face data.
- `src/facelock/auth/service.py` coordinates the whole enrollment and authentication flow.
- `data/face_encoding.pkl` is the local artifact produced by enrollment.
- `tests/` lets you verify each part without needing the GUI.

This split is important because it keeps camera access, ML logic, and persistence separate. That makes the project easier to debug and later easier to replace piece by piece.

## What Each File Should Be Used For

### `camera.py`

This file should do only webcam input.

It should:

- Open the camera.
- Read frames.
- Return a frame as an image array.
- Close the camera cleanly.

It should not know anything about embeddings or authentication. Its job is only to get pixels.

### `detector.py`

This file should decide where the face is in the frame.

It should:

- Find face locations.
- Return cropped face regions or face coordinates.
- Reject frames with no face.

This is where you can later add quality checks like “face too small,” “face too blurry,” or “more than one face detected.”

### `encoder.py`

This file should convert a detected face into a numeric embedding.

It should:

- Take a face crop or face location.
- Produce a vector representation.
- Keep the encoding format consistent.

Think of this file as the translation step between an image and a math object.

### `storage.py`

This file should manage local persistence.

It should:

- Save embeddings to disk.
- Load embeddings from disk.
- Store metadata such as timestamp, version, or capture count.

For Module 1, a simple pickle file is acceptable because the roadmap already suggests `~/.facelock/face_encoding.pkl`. Later you can move this into SQLite if needed.

### `service.py`

This file should orchestrate the workflow.

It should:

- Run enrollment.
- Run verification.
- Call the camera, detector, encoder, and storage layers in the right order.

This file is the brain of Module 1. It should be smaller than the lower-level files, not bigger.

## How The Data Should Flow

The core pipeline should look like this:

```text
Webcam frame
  ↓
Face detection
  ↓
Face crop / face location
  ↓
Face embedding
  ↓
Save to disk or compare with saved embedding
```

During enrollment, the output is stored.

During authentication, the output is compared.

That is the only major difference between the two paths.

## Enrollment Flow

Enrollment is the first user setup experience.

Suggested behavior:

1. Ask the user to face the camera.
2. Capture around 20 to 30 samples.
3. Ask for slight angle variation so the embedding is more robust.
4. Reject frames with no face or multiple faces if possible.
5. Average the embeddings or keep a small set of good embeddings.
6. Save the final representation locally.

### Why Multiple Samples Matter

A single image is fragile.

The same face looks different under changes in:

- Lighting.
- Head angle.
- Distance from camera.
- Facial expression.

Collecting multiple samples gives you a better representation of the person and reduces false rejections.

## Authentication Flow

Authentication happens when the system needs to check identity.

Suggested behavior:

1. Load the stored embedding.
2. Open the webcam.
3. Capture a fresh frame.
4. Detect the face.
5. Generate a new embedding.
6. Compare the new embedding against the stored one.
7. Decide whether the match is above or below the threshold.

### Match Threshold

You will need a threshold value.

If the distance between embeddings is small enough, treat it as a match.
If it is too far apart, treat it as a failure.

This threshold is not something you should guess once and forget. You should expect to tune it while testing on your own face in your actual lighting conditions.

## What To Build First

If you are starting from zero, create the files in this order:

1. `pyproject.toml`
2. `src/facelock/__init__.py`
3. `src/facelock/auth/__init__.py`
4. `src/facelock/auth/camera.py`
5. `src/facelock/auth/detector.py`
6. `src/facelock/auth/encoder.py`
7. `src/facelock/auth/storage.py`
8. `src/facelock/auth/service.py`
9. `tests/`
10. A small CLI entry point, such as `src/facelock/__main__.py` or `app.py`

This order is deliberate:

- Package files come first so imports work cleanly.
- Camera and detection come before storage because nothing can be saved until something is detected.
- The service layer comes after the lower-level pieces because it depends on them.
- Tests come early because they protect the prototype from becoming a pile of ad hoc scripts.

## Suggested Development Workflow

Use this cycle for every step:

1. Implement one small function.
2. Run it manually.
3. Save one known-good sample.
4. Add a small test if possible.
5. Only then move to the next function.

This is the safest way to learn because you always know what changed and why.

### Example Learning Milestones

Milestone 1: Camera preview works.

- Open webcam.
- Show live frames.
- Exit cleanly.

Milestone 2: Face detection works.

- Draw a rectangle around the detected face.
- Confirm detection on your own face.

Milestone 3: Embedding extraction works.

- Print embedding length.
- Confirm it is stable across frames.

Milestone 4: Storage works.

- Save the embedding.
- Reload it and confirm the values match.

Milestone 5: Authentication works.

- Compare fresh embedding to saved embedding.
- Print `Authenticated` when distance is within threshold.

## What To Avoid In Module 1

Do not add these yet:

- GUI pages.
- Desktop app scanning.
- Process monitoring.
- systemd integration.
- Database schema for full project state.
- App launcher wrappers.

Those belong to later modules. If you add them now, Module 1 becomes harder to debug and harder to learn from.

## How This Connects To The Full Project

Module 1 will eventually feed other parts of FaceLock:

- Module 5 will call the authentication service before launching an app.
- Module 6 may call the same service when it detects a protected process.
- Module 4 may expose a GUI button that starts enrollment.
- Module 3 may store a pointer to the enrolled face file or a future database version.

That is why Module 1 must be clean and reusable. If you keep it as a small authentication service now, the later modules can call it instead of reimplementing it.

## A Practical Implementation Shape

The architecture should be something like this:

```text
service.py
  -> camera.py
  -> detector.py
  -> encoder.py
  -> storage.py
```

And the usage pattern should look like this:

```text
enroll_face()
  -> capture many frames
  -> detect face
  -> encode face
  -> store result

verify_face()
  -> capture frame
  -> detect face
  -> encode face
  -> compare with stored result
```

That is the conceptual heart of the module.

## What Success Looks Like

Module 1 is done when you can reliably answer these questions:

1. Can the app open the webcam on your machine?
2. Can it detect your face in a live frame?
3. Can it collect several good enrollment samples?
4. Can it save an embedding to disk?
5. Can it load the embedding later?
6. Can it compare a fresh face against the saved one?
7. Can it return a clear success or failure result?

If the answer to all seven is yes, then Module 1 is complete enough to support the rest of the roadmap.

## Suggested First Commit Size

Do not start with a giant script.

Your first useful chunk should be small and boring:

1. Create the package structure.
2. Make the webcam preview work.
3. Add face detection overlay.
4. Save one embedding file.

Once that exists, you will have a real foundation instead of a concept.

## Best Way To Learn While Building

As you implement each file, ask yourself:

- What exactly is the responsibility of this file?
- What should this file never do?
- What input does it accept?
- What output does it produce?
- How can I test it in isolation?

If you keep those questions in mind, you will understand not just how to build FaceLock, but why the design is split this way.

## Short Summary

Start Module 1 by creating a small authentication package under `src/facelock/auth/`. Build the camera layer first, then detection, then encoding, then storage, then a service layer that ties it together. Keep enrollment and authentication separate in code but built from the same primitives. Do not add GUI or app-locking logic yet. Get the face prototype working by itself first, because every later module depends on it.