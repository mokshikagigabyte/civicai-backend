from .analyzer import BehavioralAnalyzer
from .legal_rag import LegalRAG
from .evaluator import ConflictEvaluator
import os
import base64
import io

class ConflictProcessor:
    def __init__(self, groq_api_key: str, index=None, metadata=None, model=None):
        print("Initializing ConflictProcessor...")
        self.analyzer = BehavioralAnalyzer(api_key=groq_api_key)
        
        # Use provided resources to avoid reloading from disk (M4 fix)
        self.rag = LegalRAG(skip_load=(index is not None))
        if index is not None and metadata is not None and model is not None:
            self.rag.index = index
            self.rag.metadata = metadata
            self.rag.model = model
            
        self.evaluator = ConflictEvaluator(api_key=groq_api_key)

    def _encode_image(self, image_bytes):
        return base64.b64encode(image_bytes).decode('utf-8')

    def extract_frames(self, video_path, num_frames=3):
        try:
            import cv2
            from PIL import Image
        except ImportError:
            print("WARNING: opencv-python or Pillow not installed. Video frame extraction disabled.")
            return []
        
        video = cv2.VideoCapture(video_path)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = []
        
        if total_frames > 0:
            # Extract frames at 10%, 50%, and 90%
            indices = [int(total_frames * 0.1), int(total_frames * 0.5), int(total_frames * 0.9)]
            for idx in indices:
                video.set(cv2.CAP_PROP_POS_FRAMES, idx)
                success, frame = video.read()
                if success:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame_rgb)
                    # Resize for faster processing
                    pil_img.thumbnail((800, 800))
                    buffer = io.BytesIO()
                    pil_img.save(buffer, format="JPEG")
                    frames.append(self._encode_image(buffer.getvalue()))
        video.release()
        return frames

    async def process_conflict(self, party_a_text: str, party_b_text: str, files: list = None):
        # 1. Behavioral Analysis — parallel API calls (M3 fix)
        print("Analyzing behavior...")
        import asyncio
        a_task = self.analyzer.analyze_both(party_a_text)
        b_task = self.analyzer.analyze_both(party_b_text)
        
        a_data, b_data = await asyncio.gather(a_task, b_task)
        
        behavioral_data = {
            "party_a": {"sentiment": a_data["sentiment"], "toxicity": a_data["toxicity"]},
            "party_b": {"sentiment": b_data["sentiment"], "toxicity": b_data["toxicity"]},
        }

        # 2. Extract and Encode Visual Proof
        images_b64 = []
        if files:
            for file in files:
                f_type = getattr(file, 'type', None) or ''
                f_content = file.getvalue()
                
                if not f_content:
                    continue

                if f_type.startswith('image/'):
                    images_b64.append(self._encode_image(f_content))
                elif f_type.startswith('video/'):
                    # Save temp video to extract frames
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                        tmp.write(f_content)
                        tmp_path = tmp.name
                    frames = self.extract_frames(tmp_path)
                    images_b64.extend(frames)
                    import os
                    os.unlink(tmp_path)
                elif not f_type:
                    # Fallback: try to treat as image if type is missing
                    try:
                        images_b64.append(self._encode_image(f_content))
                    except:
                        pass

        # 3. Legal RAG Retrieval
        print("Retrieving legal context...")
        combined_query = f"{party_a_text} {party_b_text}"
        legal_results = self.rag.retrieve(combined_query, top_k=5)
        legal_context = self.rag.format_context(legal_results)

        # 4. Conflict Evaluation
        print("Evaluating conflict...")
        report = await self.evaluator.evaluate(
            party_a=party_a_text,
            party_b=party_b_text,
            behavioral_data=behavioral_data,
            legal_context=legal_context,
            images=images_b64
        )

        return report

if __name__ == "__main__":
    # Test script — load key from environment
    import os
    from dotenv import load_dotenv
    load_dotenv()
    API_KEY = os.getenv("GROQ_API_KEY", "")
    processor = ConflictProcessor(API_KEY)
    
    test_a = "You hit my car from behind! You should pay for the damages. You are such a reckless driver!"
    test_b = "I didn't hit you! You stopped suddenly without any indicator. You're the one at fault!"
    
    result = processor.process_conflict(test_a, test_b)
    if result:
        print(result.model_dump_json(indent=2))
