"""
GitHub repository operations management
"""
import os
import base64
import re
import yaml
from github import Github, GithubException
from FlaskApp.config import Config

def get_github_manager():
    """Factory function to get GitHub manager instance"""
    return GitHubRepoManager(Config.GITHUB_TOKEN, Config.REPO_NAME, Config.BRANCH)

class GitHubRepoManager:
    """Manages file operations on GitHub repository"""
    
    def __init__(self, token, repo_name, branch='main'):
        self.g = Github(token)
        self.repo = self.g.get_repo(repo_name)
        self.branch = branch
    
    def get_file_content(self, file_path):
        """Get file content from GitHub"""
        try:
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return {
                'content': content,
                'sha': file_content.sha,
                'path': file_path
            }
        except GithubException as e:
            print(f"Error getting file {file_path}: {e}")
            return None
    
    def update_file(self, file_path, content, commit_message, sha=None):
        """Update file in GitHub repo"""
        try:
            if sha:
                self.repo.update_file(
                    file_path,
                    commit_message,
                    content,
                    sha,
                    branch=self.branch
                )
            else:
                self.repo.create_file(
                    file_path,
                    commit_message,
                    content,
                    branch=self.branch
                )
            return True
        except GithubException as e:
            print(f"Error updating file {file_path}: {e}")
            return False
    
    def delete_file(self, file_path, commit_message):
        """Delete file from GitHub repo"""
        try:
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            self.repo.delete_file(
                file_path,
                commit_message,
                file_content.sha,
                branch=self.branch
            )
            return True
        except GithubException as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def list_posts(self):
        """List all blog posts"""
        try:
            contents = self.repo.get_contents("_posts", ref=self.branch)
            posts = []
            for content in contents:
                if content.name.endswith(('.html', '.md', '.markdown')):
                    posts.append({
                        'name': content.name,
                        'path': content.path,
                        'sha': content.sha,
                        'size': content.size
                    })
            return sorted(posts, key=lambda x: x['name'], reverse=True)
        except GithubException as e:
            print(f"Error listing posts: {e}")
            return []
    
    def list_pages(self):
        """List all pages (non-post HTML files in root)"""
        try:
            contents = self.repo.get_contents("", ref=self.branch)
            pages = []
            for content in contents:
                if content.name.endswith('.html') and content.name not in ['index.html']:
                    pages.append({
                        'name': content.name,
                        'path': content.path,
                        'sha': content.sha
                    })
            return pages
        except GithubException as e:
            print(f"Error listing pages: {e}")
            return []
    
    def get_config_yml(self):
        """Get _config.yml content"""
        return self.get_file_content('_config.yml')
    
    def update_config_yml(self, config_dict, commit_message="Update blog configuration"):
        """Update _config.yml"""
        config_file = self.get_config_yml()
        if not config_file:
            return False
        
        yaml_content = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
        return self.update_file('_config.yml', yaml_content, commit_message, config_file['sha'])
    
    def parse_front_matter(self, content):
        """Parse Jekyll front matter from content"""
        if not content.startswith('---'):
            return None, content
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None, content
        
        try:
            front_matter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return front_matter, body
        except yaml.YAMLError:
            return None, content
    
    def create_front_matter(self, front_matter_dict, body):
        """Create Jekyll file with front matter"""
        fm = '---\n'
        fm += yaml.dump(front_matter_dict, default_flow_style=False, allow_unicode=True)
        fm += '---\n\n'
        return fm + body
    
    def extract_content_section(self, content, section_id):
        """Extract a specific content section by ID"""
        pattern = rf'<!-- {section_id} -->(.*?)<!-- /{section_id} -->'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def update_content_section(self, content, section_id, new_section_content):
        """Update a specific content section"""
        pattern = rf'(<!-- {section_id} -->)(.*?)(<!-- /{section_id} -->)'
        replacement = rf'\1\n{new_section_content}\n\3'
        updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
        return updated
    
    def trigger_workflow(self, workflow_name='mainBlog.yml'):
        """Trigger GitHub Actions workflow"""
        try:
            workflow = self.repo.get_workflow(workflow_name)
            workflow.create_dispatch(ref=self.branch)
            return True
        except GithubException as e:
            print(f"Error triggering workflow: {e}")
            return False
