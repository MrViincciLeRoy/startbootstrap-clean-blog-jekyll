"""
Theme management routes
Add these to FlaskApp/core/config_management/routes.py
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import datetime
from FlaskApp.services.github_manager import get_github_manager
from FlaskApp.services.theme_manager import ThemeManager

theme_manager = ThemeManager()

def setup_theme_routes(bp):
    """Setup theme management routes"""
    
    @bp.route('/theme-customizer', methods=['GET'])
    @login_required
    def theme_customizer():
        """Theme customizer interface"""
        gh = get_github_manager()
        
        # Get current theme from config
        import yaml
        config_file = gh.get_config_yml()
        current_theme = 'default'
        theme_colors = None
        
        if config_file:
            config = yaml.safe_load(config_file['content'])
            current_theme = config.get('active_theme', 'default')
            theme_colors = config.get('theme_colors', None)
        
        # Get all available themes
        all_themes = theme_manager.get_all_themes()
        
        # If no custom colors, use theme defaults
        if not theme_colors:
            theme_colors = theme_manager.get_theme(current_theme)
        
        return render_template('theme_customizer.html',
                             current_theme=current_theme,
                             theme_colors=theme_colors,
                             all_themes=all_themes,
                             available_fonts=theme_manager.AVAILABLE_FONTS)
    
    @bp.route('/theme-customizer/preview', methods=['POST'])
    @login_required
    def preview_theme():
        """Generate preview CSS for theme"""
        try:
            theme_config = {
                'primary_color': request.form.get('primary_color'),
                'secondary_color': request.form.get('secondary_color'),
                'background_color': request.form.get('background_color'),
                'text_color': request.form.get('text_color'),
                'navbar_bg': request.form.get('navbar_bg'),
                'navbar_text': request.form.get('navbar_text'),
                'footer_bg': request.form.get('footer_bg'),
                'footer_text': request.form.get('footer_text'),
                'link_color': request.form.get('link_color'),
                'link_hover': request.form.get('link_hover'),
                'masthead_overlay': float(request.form.get('masthead_overlay', 0.5)),
                'font_family_base': request.form.get('font_family_base', 'Lora'),
                'font_family_headings': request.form.get('font_family_headings', 'Open Sans')
            }
            
            css = theme_manager.generate_css_variables(theme_config)
            
            return jsonify({
                'status': 'success',
                'css': css
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @bp.route('/theme-customizer/apply', methods=['POST'])
    @login_required
    def apply_theme():
        """Apply theme to site configuration"""
        gh = get_github_manager()
        
        try:
            theme_config = {
                'primary_color': request.form.get('primary_color'),
                'secondary_color': request.form.get('secondary_color'),
                'background_color': request.form.get('background_color'),
                'text_color': request.form.get('text_color'),
                'navbar_bg': request.form.get('navbar_bg'),
                'navbar_text': request.form.get('navbar_text'),
                'footer_bg': request.form.get('footer_bg'),
                'footer_text': request.form.get('footer_text'),
                'link_color': request.form.get('link_color'),
                'link_hover': request.form.get('link_hover'),
                'masthead_overlay': float(request.form.get('masthead_overlay', 0.5)),
                'font_family_base': request.form.get('font_family_base', 'Lora'),
                'font_family_headings': request.form.get('font_family_headings', 'Open Sans')
            }
            
            # Save as custom theme if name provided
            custom_name = request.form.get('save_as_custom')
            if custom_name:
                theme_config['name'] = custom_name
                if theme_manager.save_custom_theme(custom_name, theme_config):
                    flash(f'✓ Custom theme "{custom_name}" saved successfully!', 'success')
            
            # Apply to GitHub config
            if theme_manager.apply_theme_to_config(gh, theme_config):
                flash('✓ Theme applied successfully! Changes will be visible after Jekyll rebuild.', 'success')
                return redirect(url_for('config_management.theme_customizer'))
            else:
                flash('✗ Error applying theme to configuration', 'error')
                
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        
        return redirect(url_for('config_management.theme_customizer'))
    
    @bp.route('/theme-customizer/load/<theme_name>', methods=['GET'])
    @login_required
    def load_theme(theme_name):
        """Load a theme configuration"""
        theme = theme_manager.get_theme(theme_name)
        return jsonify({
            'status': 'success',
            'theme': theme
        })
    
    @bp.route('/theme-customizer/delete/<theme_name>', methods=['POST'])
    @login_required
    def delete_theme(theme_name):
        """Delete a custom theme"""
        # Don't allow deleting default themes
        if theme_name in theme_manager.DEFAULT_THEMES:
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete default themes'
            }), 400
        
        if theme_manager.delete_custom_theme(theme_name):
            return jsonify({
                'status': 'success',
                'message': f'Theme "{theme_name}" deleted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to delete theme'
            }), 500
    
    @bp.route('/api/themes', methods=['GET'])
    @login_required
    def get_themes_api():
        """API endpoint to get all themes"""
        all_themes = theme_manager.get_all_themes()
        return jsonify({
            'status': 'success',
            'themes': all_themes
        })
