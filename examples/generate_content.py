from src.content.generator import ContentGenerator

def main():
    # Initialize the content generator
    generator = ContentGenerator()
    
    # Load content from a source directory
    # This directory should contain text files, markdown, etc. that will be used
    # as source material for generating posts
    if not generator.load_content_source("content_sources"):
        print("Failed to load content source")
        return
        
    # Generate posts with different parameters
    
    # Basic post
    post = generator.generate_post(
        "Create an engaging tweet about artificial intelligence"
    )
    print("\nBasic post:")
    print(post)
    
    # Post with length control
    post = generator.generate_post(
        "Create a tweet about machine learning",
        max_length=140  # Twitter-style length
    )
    print("\nLength-controlled post:")
    print(post)
    
    # Post with tone and style
    post = generator.generate_post(
        "Create a post about data science",
        tone="professional",
        style="educational"
    )
    print("\nStyled post:")
    print(post)
    
if __name__ == "__main__":
    main() 