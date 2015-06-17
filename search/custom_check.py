
import re

def check_custom(statement):
    statement = statement.lower()
    q3c_result = {'returncode': '200', 'error': '', 'sql': ''}
    q3c_queries = ['q3c_join','q3c_ellipse_join','q3c_radial_query','q3c_ellipse_query','q3c_poly_query']
    # q3c_expressions = '[q3c_ang2ipix','q3c_dist','q3c_ipix2ang','q3c_pixarea','q3c_ipixcenter']
    if re.match('q3c_', statement):
        q3c_statement = re.match(r'(q3c_[a-z_]+)\([a-z0-9,\.]+\)', statement)
        if q3c_statement.group(1) in q3c_queries:
            # proper q3c query with parameters
            q3c_result['sql'] = statement
            return q3c_result
        else:
            # q3c-like statement but not a recognized q3c keyword
            q3c_result = {'returncode': '400', 'error': 'not a propoer q3c query', 'sql': ''}
            return q3c_result
    else: 
        # no attempt to use q3c
        return q3c_result
