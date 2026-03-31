from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import uuid
import os
from scraper.google_maps import GoogleMapsScraper
from scraper.exporter import DataExporter
from models.database import db, Business, ScrapeJob
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///scraper.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Active scraping jobs
active_jobs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start-scrape', methods=['POST'])
def start_scrape():
    data = request.json
    keyword = data.get('keyword', '').strip()
    location = data.get('location', '').strip()
    max_results = data.get('max_results', 100)
    
    if not keyword or not location:
        return jsonify({'error': 'Keyword and location are required'}), 400
    
    job_id = str(uuid.uuid4())
    
    # Save job to DB
    with app.app_context():
        job = ScrapeJob(
            job_id=job_id,
            keyword=keyword,
            location=location,
            status='running',
            total_found=0
        )
        db.session.add(job)
        db.session.commit()
    
    # Start scraping in background thread
    thread = threading.Thread(
        target=run_scrape_job,
        args=(job_id, keyword, location, max_results)
    )
    thread.daemon = True
    thread.start()
    active_jobs[job_id] = thread
    
    return jsonify({'job_id': job_id, 'status': 'started'})

def run_scrape_job(job_id, keyword, location, max_results):
    """Background scraping job with real-time updates"""
    with app.app_context():
        scraper = GoogleMapsScraper()
        
        def progress_callback(data):
            socketio.emit('scrape_progress', {
                'job_id': job_id,
                'type': data.get('type'),
                'message': data.get('message'),
                'business': data.get('business'),
                'count': data.get('count', 0),
                'total': data.get('total', 0)
            })
        
        try:
            businesses = scraper.scrape(
                keyword=keyword,
                location=location,
                max_results=max_results,
                callback=progress_callback
            )
            
            # Save to database
            saved_count = 0
            for biz in businesses:
                try:
                    existing = Business.query.filter_by(
                        place_id=biz.get('place_id', ''),
                        job_id=job_id
                    ).first()
                    
                    if not existing:
                        business = Business(
                            job_id=job_id,
                            name=biz.get('name', ''),
                            rating=biz.get('rating'),
                            review_count=biz.get('review_count', 0),
                            business_type=biz.get('type', ''),
                            address=biz.get('address', ''),
                            phone=biz.get('phone', ''),
                            website=biz.get('website', ''),
                            hours=biz.get('hours', ''),
                            price_level=biz.get('price_level', ''),
                            place_id=biz.get('place_id', ''),
                            latitude=biz.get('lat'),
                            longitude=biz.get('lng'),
                            maps_url=biz.get('maps_url', ''),
                            is_claimed=biz.get('is_claimed', False),
                            status=biz.get('status', ''),
                            thumbnail=biz.get('thumbnail', '')
                        )
                        db.session.add(business)
                        saved_count += 1
                except Exception as e:
                    print(f"Error saving business: {e}")
            
            # Update job status
            job = ScrapeJob.query.filter_by(job_id=job_id).first()
            if job:
                job.status = 'completed'
                job.total_found = saved_count
            
            db.session.commit()
            
            socketio.emit('scrape_complete', {
                'job_id': job_id,
                'total': saved_count,
                'message': f'Successfully scraped {saved_count} businesses!'
            })
            
        except Exception as e:
            job = ScrapeJob.query.filter_by(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                db.session.commit()
            
            socketio.emit('scrape_error', {
                'job_id': job_id,
                'error': str(e)
            })

@app.route('/api/results', methods=['GET'])
def get_results():
    job_id = request.args.get('job_id')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    # Advanced filters
    filters = {
        'min_rating': request.args.get('min_rating', type=float),
        'max_rating': request.args.get('max_rating', type=float),
        'min_reviews': request.args.get('min_reviews', type=int),
        'max_reviews': request.args.get('max_reviews', type=int),
        'business_type': request.args.get('business_type'),
        'has_phone': request.args.get('has_phone'),
        'has_website': request.args.get('has_website'),
        'is_claimed': request.args.get('is_claimed'),
        'price_level': request.args.get('price_level'),
        'status': request.args.get('status'),
        'keyword_in_reviews': request.args.get('keyword_in_reviews'),
        'sort_by': request.args.get('sort_by', 'rating'),
        'sort_order': request.args.get('sort_order', 'desc'),
    }
    
    query = Business.query.filter_by(job_id=job_id)
    
    # Apply filters
    if filters['min_rating']:
        query = query.filter(Business.rating >= filters['min_rating'])
    if filters['max_rating']:
        query = query.filter(Business.rating <= filters['max_rating'])
    if filters['min_reviews']:
        query = query.filter(Business.review_count >= filters['min_reviews'])
    if filters['max_reviews']:
        query = query.filter(Business.review_count <= filters['max_reviews'])
    if filters['business_type']:
        query = query.filter(Business.business_type.ilike(f"%{filters['business_type']}%"))
    if filters['has_phone'] == 'true':
        query = query.filter(Business.phone != '')
    if filters['has_website'] == 'true':
        query = query.filter(Business.website != '')
    if filters['is_claimed'] == 'true':
        query = query.filter(Business.is_claimed == True)
    if filters['price_level']:
        query = query.filter(Business.price_level == filters['price_level'])
    if filters['status']:
        query = query.filter(Business.status.ilike(f"%{filters['status']}%"))
    
    # Sorting
    sort_col = getattr(Business, filters['sort_by'], Business.rating)
    if filters['sort_order'] == 'desc':
        query = query.order_by(sort_col.desc().nullslast())
    else:
        query = query.order_by(sort_col.asc().nullsfirst())
    
    total = query.count()
    businesses = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': businesses.pages,
        'results': [b.to_dict() for b in businesses.items]
    })

@app.route('/api/export', methods=['GET'])
def export_data():
    job_id = request.args.get('job_id')
    format_type = request.args.get('format', 'csv')
    
    businesses = Business.query.filter_by(job_id=job_id).all()
    data = [b.to_dict() for b in businesses]
    
    exporter = DataExporter()
    
    if format_type == 'csv':
        filepath = exporter.to_csv(data, job_id)
        return send_file(filepath, as_attachment=True, download_name=f'businesses_{job_id[:8]}.csv')
    elif format_type == 'excel':
        filepath = exporter.to_excel(data, job_id)
        return send_file(filepath, as_attachment=True, download_name=f'businesses_{job_id[:8]}.xlsx')
    elif format_type == 'json':
        filepath = exporter.to_json(data, job_id)
        return send_file(filepath, as_attachment=True, download_name=f'businesses_{job_id[:8]}.json')
    
    return jsonify({'error': 'Invalid format'}), 400

@app.route('/api/stats', methods=['GET'])
def get_stats():
    job_id = request.args.get('job_id')
    businesses = Business.query.filter_by(job_id=job_id).all()
    
    if not businesses:
        return jsonify({'error': 'No data found'}), 404
    
    ratings = [b.rating for b in businesses if b.rating]
    reviews = [b.review_count for b in businesses if b.review_count]
    types = {}
    
    for b in businesses:
        if b.business_type:
            types[b.business_type] = types.get(b.business_type, 0) + 1
    
    return jsonify({
        'total': len(businesses),
        'avg_rating': round(sum(ratings)/len(ratings), 2) if ratings else 0,
        'total_reviews': sum(reviews),
        'with_phone': sum(1 for b in businesses if b.phone),
        'with_website': sum(1 for b in businesses if b.website),
        'claimed': sum(1 for b in businesses if b.is_claimed),
        'top_types': sorted(types.items(), key=lambda x: x[1], reverse=True)[:10],
        'rating_distribution': {
            '5': sum(1 for b in businesses if b.rating and b.rating >= 4.5),
            '4': sum(1 for b in businesses if b.rating and 3.5 <= b.rating < 4.5),
            '3': sum(1 for b in businesses if b.rating and 2.5 <= b.rating < 3.5),
            '2': sum(1 for b in businesses if b.rating and 1.5 <= b.rating < 2.5),
            '1': sum(1 for b in businesses if b.rating and b.rating < 1.5),
        }
    })

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    jobs = ScrapeJob.query.order_by(ScrapeJob.created_at.desc()).limit(20).all()
    return jsonify([{
        'job_id': j.job_id,
        'keyword': j.keyword,
        'location': j.location,
        'status': j.status,
        'total_found': j.total_found,
        'created_at': j.created_at.isoformat() if j.created_at else None
    } for j in jobs])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
