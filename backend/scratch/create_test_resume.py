import fitz

doc = fitz.open()
page = doc.new_page()

text = """
John Doe
Email: john.doe@example.com
Phone: +91 9999999999
Location: Bengaluru, India

Skills: Python, React, Next.js, Node.js, SQL, Machine Learning, Robotics

Experience:
Software Engineer Intern at Robotics Corp (Jan 2024 - Present)
- Developed computer vision algorithms for autonomous navigation.
- Built a web interface for robot telemetry using React and Next.js.
- Used Python and PyTorch.

Education:
Bachelor of Technology in Computer Science, IIT Bombay (2021 - 2025)

Projects:
Autonomous Rover
- Built a self-driving rover using ROS, Python, and C++.
"""

page.insert_text((50, 50), text, fontsize=11)
doc.save("test_resume.pdf")
doc.close()
print("Resume PDF created!")
